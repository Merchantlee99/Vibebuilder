#!/usr/bin/env python3
"""Operational review-gate workflow helpers for normal and high-risk work."""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import activity_bridge
    import event_log
    import runtime_gate
    import session_state
else:  # pragma: no cover - package import path
    from . import activity_bridge, event_log, runtime_gate, session_state


REVIEWS_DIR = Path(".codex/reviews")
VALID_TIERS = {"normal", "high-risk"}


def repo_root() -> Path:
    return event_log.repo_root()


def review_dir(root: Path) -> Path:
    path = root / REVIEWS_DIR
    path.mkdir(parents=True, exist_ok=True)
    return path


def utc_stamp() -> str:
    return time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())


def latest_review_path(root: Path) -> Path | None:
    candidates = sorted(
        path
        for path in review_dir(root).glob("*.md")
        if path.name.lower() != "readme.md"
    )
    return candidates[-1] if candidates else None


def normalize_review_path(root: Path, raw: str | None) -> Path:
    if not raw:
        return review_dir(root) / f"review-{utc_stamp()}.md"
    candidate = Path(raw)
    if not candidate.is_absolute():
        if "/" not in raw and "\\" not in raw:
            candidate = review_dir(root) / raw
        else:
            candidate = (root / candidate).resolve()
    else:
        candidate = candidate.resolve()
    reviews_root = review_dir(root).resolve()
    if not str(candidate).startswith(str(reviews_root)):
        raise ValueError("review file must live under .codex/reviews/")
    return candidate


def extract_heading_bullets(path: Path, heading: str) -> list[str]:
    if not path.exists():
        return []
    items: list[str] = []
    active = False
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        stripped = raw_line.strip()
        if stripped == heading:
            active = True
            continue
        if active and stripped.startswith("## "):
            break
        if active and stripped.startswith("- "):
            items.append(stripped[2:].strip())
    return items


def git_changed_files(root: Path, base: str) -> list[str]:
    if not runtime_gate.git_repo_initialized(root):
        return []
    files: list[str] = []
    if runtime_gate.head_commit_exists(root):
        proc = subprocess.run(
            ["git", "diff", "--name-only", base],
            cwd=str(root),
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode == 0:
            files.extend(line.strip() for line in proc.stdout.splitlines() if line.strip())
    proc = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard"],
        cwd=str(root),
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode == 0:
        files.extend(line.strip() for line in proc.stdout.splitlines() if line.strip())
    seen: list[str] = []
    for item in files:
        if item not in seen and item != ".codex/context/session.json":
            seen.append(item)
    return seen


def render_review_request(
    *,
    tier: str,
    producer: str,
    producer_session: str,
    files: list[str],
    validations: list[str],
    rollback_items: list[str],
) -> str:
    lines = [
        "Reviewer: <required-reviewer>",
        f"Producer: {producer}",
        "Reviewer-Session: <required-reviewer-session>",
        f"Producer-Session: {producer_session}",
        f"Review-Tier: {tier}",
        f"Requested-At: {utc_stamp()}",
        "",
        "Verdict: pending",
        "",
        "Files:",
    ]
    lines.extend(f"- {item}" for item in files or ["<required-file-list>"])
    lines.extend(
        [
            "",
            "Findings:",
            "- <reviewer: add findings or replace with none>",
            "",
            "Validation:",
        ]
    )
    lines.extend(f"- producer context: {item}" for item in validations)
    lines.append("- <reviewer-run command and result>")
    lines.extend(
        [
            "",
            "Risks:",
            "- <reviewer: remaining risk or none>",
        ]
    )
    if tier == "high-risk":
        lines.extend(["", "Rollback:"])
        lines.extend(f"- producer context: {item}" for item in rollback_items)
        lines.append("- <reviewer: confirm rollback path and trigger>")
    return "\n".join(lines) + "\n"


def prepare_review(
    root: Path,
    *,
    tier: str,
    producer: str,
    review_file: str | None,
    base: str,
    files: list[str],
    validations: list[str],
    rollback_items: list[str],
    force: bool,
) -> int:
    if tier not in VALID_TIERS:
        print("review gate only applies to normal or high-risk work", file=sys.stderr)
        return 2
    activity_bridge.sync(root)
    runtime = runtime_gate.load_runtime(root)
    start_violations = runtime_gate.artifact_violations(root, tier)
    gate_result = runtime_gate.enforce_or_advise(runtime.get("mode", "advisory"), start_violations)
    if gate_result == 2:
        return gate_result

    target = normalize_review_path(root, review_file)
    if target.exists() and not force:
        print(f"review file already exists: {target}", file=sys.stderr)
        return 1

    producer_session = session_state.resolve_session_id(root)
    changed_files = files or git_changed_files(root, base)
    producer_validations = validations or extract_heading_bullets(root / "Implement.md", "## Validation")
    producer_rollbacks = rollback_items or extract_heading_bullets(root / "Plan.md", "## Rollback")
    content = render_review_request(
        tier=tier,
        producer=producer,
        producer_session=producer_session,
        files=changed_files,
        validations=producer_validations or ["<producer-validation-context>"],
        rollback_items=producer_rollbacks or ["<producer-rollback-context>"],
    )
    target.write_text(content, encoding="utf-8")
    event_log.append_event(
        kind="review-requested",
        actor=producer,
        summary=f"review requested for {tier} work",
        files=[str(target.relative_to(root))],
        stage="review",
        detail={
            "tier": tier,
            "producer_session": producer_session,
            "changed_files": changed_files,
        },
        root=root,
    )
    print(target)
    return 0


def finalize_review(root: Path, *, tier: str, review_file: str | None, actor: str) -> int:
    if tier not in VALID_TIERS:
        print("review gate only applies to normal or high-risk work", file=sys.stderr)
        return 2
    activity_bridge.sync(root)
    resolved = runtime_gate.resolve_review_file(root, review_file)
    violations = runtime_gate.completion_violations(root, tier, resolved)
    if violations:
        print("BLOCKED")
        for violation in violations:
            print(f"- {violation}")
        event_log.append_event(
            kind="review-gate-blocked",
            actor=actor,
            summary=f"review gate blocked for {tier} work",
            files=[resolved] if resolved else [],
            stage="review",
            detail={"tier": tier, "violations": violations},
            root=root,
        )
        return 2
    print("ok")
    event_log.append_event(
        kind="review-gate-passed",
        actor=actor,
        summary=f"review gate passed for {tier} work",
        files=[resolved] if resolved else [],
        stage="review",
        detail={"tier": tier},
        root=root,
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)

    prepare = sub.add_parser("prepare")
    prepare.add_argument("--tier", required=True, choices=sorted(VALID_TIERS))
    prepare.add_argument("--producer", default="main-codex")
    prepare.add_argument("--review-file", default=None)
    prepare.add_argument("--base", default="HEAD")
    prepare.add_argument("--file", dest="files", action="append", default=[])
    prepare.add_argument("--validation", action="append", default=[])
    prepare.add_argument("--rollback", action="append", default=[])
    prepare.add_argument("--force", action="store_true")

    finalize = sub.add_parser("finalize")
    finalize.add_argument("--tier", required=True, choices=sorted(VALID_TIERS))
    finalize.add_argument("--review-file", default="latest")
    finalize.add_argument("--actor", default="main-codex")

    args = parser.parse_args()
    root = repo_root()

    if args.cmd == "prepare":
        return prepare_review(
            root,
            tier=args.tier,
            producer=args.producer,
            review_file=args.review_file,
            base=args.base,
            files=args.files,
            validations=args.validation,
            rollback_items=args.rollback,
            force=args.force,
        )
    return finalize_review(root, tier=args.tier, review_file=args.review_file, actor=args.actor)


if __name__ == "__main__":
    raise SystemExit(main())
