#!/usr/bin/env python3
"""Consume runtime mode and review matrix to enforce delivery checks."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import activity_bridge
    from manifest_loader import load as load_manifest, ManifestError
else:  # pragma: no cover - package import path
    from . import activity_bridge
    from .manifest_loader import load as load_manifest, ManifestError


VALID_MODES = {"advisory", "enforced"}
REVIEW_REQUIRED_SECTIONS = ["Verdict:", "Files:", "Findings:", "Validation:", "Risks:"]
REVIEW_REQUIRED_METADATA = ["Reviewer", "Producer", "Reviewer-Session", "Producer-Session"]
REVIEW_LIST_SECTIONS = ["Files", "Findings", "Validation", "Risks", "Rollback"]
REVIEW_ALLOWED_VERDICTS = {"accept", "revise", "reject"}
REVIEW_PLACEHOLDER_WORDS = ("pending", "tbd", "todo", "to confirm", "to fill", "required")


def repo_root() -> Path:
    current = Path.cwd().resolve()
    for candidate in (current, *current.parents):
        if (candidate / ".codex").exists() or (candidate / ".git").exists():
            return candidate
    return current


def load_runtime(root: Path) -> dict:
    return json.loads((root / ".codex" / "runtime.json").read_text(encoding="utf-8"))


def save_runtime(root: Path, runtime: dict) -> None:
    (root / ".codex" / "runtime.json").write_text(
        json.dumps(runtime, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def enforce_or_advise(mode: str, violations: list[str]) -> int:
    if not violations:
        print("ok")
        return 0
    label = "BLOCKED" if mode == "enforced" else "ADVISORY"
    print(label)
    for violation in violations:
        print(f"- {violation}")
    return 2 if mode == "enforced" else 0


def ensure_file(root: Path, rel: str, minimum_bytes: int = 40) -> str | None:
    path = root / rel
    if not path.exists():
        return f"missing required artifact: {rel}"
    if path.stat().st_size < minimum_bytes:
        return f"artifact too small: {rel}"
    return None


def ensure_contains(root: Path, rel: str, pattern: str, label: str) -> str | None:
    path = root / rel
    if not path.exists():
        return f"missing required artifact: {rel}"
    content = path.read_text(encoding="utf-8")
    if pattern not in content:
        return f"{label} missing from {rel}"
    return None


def load_review_matrix(root: Path) -> dict:
    try:
        return load_manifest(root / ".codex" / "manifests" / "review-matrix.yaml")
    except ManifestError as exc:
        raise SystemExit(f"invalid review matrix: {exc}") from exc


def load_mode_policy(root: Path) -> dict:
    try:
        return load_manifest(root / ".codex" / "manifests" / "mode-policy.yaml")
    except ManifestError as exc:
        raise SystemExit(f"invalid mode policy: {exc}") from exc


def deployment_profile(runtime: dict) -> str:
    return str(runtime.get("deployment_profile", "template") or "template")


def git_repo_initialized(root: Path) -> bool:
    return (root / ".git").exists()


def head_commit_exists(root: Path) -> bool:
    if not git_repo_initialized(root):
        return False
    proc = subprocess.run(
        ["git", "rev-parse", "--verify", "HEAD"],
        cwd=str(root),
        capture_output=True,
        text=True,
        check=False,
    )
    return proc.returncode == 0


def profile_mode_violations(root: Path, runtime: dict, target_mode: str) -> list[str]:
    policy = load_mode_policy(root)
    profile = deployment_profile(runtime)
    profiles = policy.get("profiles", {})
    profile_data = profiles.get(profile, {})
    allowed = profile_data.get("allowed_runtime_modes", [])
    violations: list[str] = []
    if target_mode not in allowed:
        violations.append(f"deployment profile '{profile}' does not allow runtime mode '{target_mode}'")
        return violations
    if target_mode != "enforced":
        return violations

    for requirement in profile_data.get("enforced_requires", []):
        if requirement == "git_repo_initialized" and not git_repo_initialized(root):
            violations.append("enforced mode requires an initialized git repository")
        elif requirement == "head_commit_exists" and not head_commit_exists(root):
            violations.append("enforced mode requires at least one git commit")
    return violations


def parse_review_metadata(content: str) -> dict[str, str]:
    metadata: dict[str, str] = {}
    for line in content.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        if key in REVIEW_REQUIRED_METADATA and value.strip():
            metadata[key] = value.strip()
    return metadata


def parse_review_sections(content: str) -> dict[str, object]:
    sections: dict[str, object] = {"Verdict": ""}
    current: str | None = None
    for name in REVIEW_LIST_SECTIONS:
        sections[name] = []

    for raw_line in content.splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped:
            continue
        if current and stripped.startswith("- "):
            sections[current].append(stripped[2:].strip())
            continue
        if ":" in stripped:
            key, value = stripped.split(":", 1)
            key = key.strip()
            value = value.strip()
            if key == "Verdict":
                sections["Verdict"] = value
                current = None
                continue
            if key in REVIEW_LIST_SECTIONS:
                current = key
                if value:
                    item = value[1:].strip() if value.startswith("-") else value
                    if item:
                        sections[key].append(item)
                continue
            current = None
    return sections


def is_placeholder_text(value: str, *, allow_none: bool = False) -> bool:
    normalized = " ".join((value or "").strip().lower().split())
    if not normalized:
        return True
    if allow_none and normalized == "none":
        return False
    if "<" in value and ">" in value:
        return True
    if normalized in {"pending", "tbd", "todo", "n/a", "na"}:
        return True
    return any(token in normalized for token in REVIEW_PLACEHOLDER_WORDS)


def list_section_violations(label: str, items: list[str], *, allow_none: bool) -> list[str]:
    violations: list[str] = []
    if not items:
        return [f"review file missing entries under {label}:"]
    if allow_none and len(items) == 1 and items[0].strip().lower() == "none":
        return []
    for item in items:
        if is_placeholder_text(item, allow_none=allow_none):
            violations.append(f"review file has placeholder content under {label}: {item}")
    return violations


def artifact_violations(root: Path, tier: str) -> list[str]:
    review_matrix = load_review_matrix(root)
    tiers = review_matrix.get("tiers", {})
    tier_data = tiers.get(tier, {})
    required = tier_data.get("required_artifacts", [])
    violations: list[str] = []
    for artifact in required:
        if artifact == "targeted-validation":
            violation = ensure_contains(root, "Implement.md", "## Validation", "validation section")
        elif artifact == "rollback-plan":
            violation = ensure_contains(root, "Plan.md", "## Rollback", "rollback plan")
        elif artifact == "design-options":
            violation = ensure_file(root, "Design-Options.md")
        elif isinstance(artifact, str) and artifact.endswith(".md"):
            violation = ensure_file(root, artifact)
        else:
            violation = None
        if violation:
            violations.append(violation)
    return violations


def resolve_review_file(root: Path, review_file: str | None) -> str | None:
    if review_file not in (None, "latest"):
        raw = Path(review_file)
        if not raw.is_absolute() and "/" not in review_file and "\\" not in review_file:
            return str((root / ".codex" / "reviews" / review_file).relative_to(root))
        if raw.is_absolute():
            return str(raw.resolve().relative_to(root.resolve()))
        return review_file
    candidates = sorted(
        path
        for path in (root / ".codex" / "reviews").glob("*.md")
        if path.name.lower() != "readme.md"
    )
    if not candidates:
        return None
    return str(candidates[-1].relative_to(root))


def review_file_violations(root: Path, tier: str, review_file: str) -> list[str]:
    path = (root / review_file).resolve()
    reviews_root = (root / ".codex" / "reviews").resolve()
    violations: list[str] = []
    if not path.exists():
        return [f"review file missing: {review_file}"]
    if not str(path).startswith(str(reviews_root)):
        violations.append("review file must live under .codex/reviews/")
    content = path.read_text(encoding="utf-8")
    if len(content) < 250:
        violations.append("review file is too small to be credible")
    for section in REVIEW_REQUIRED_SECTIONS:
        if section not in content:
            violations.append(f"review file missing section: {section}")
    metadata = parse_review_metadata(content)
    for field in REVIEW_REQUIRED_METADATA:
        if not metadata.get(field):
            violations.append(f"review file missing metadata: {field}:")
        elif is_placeholder_text(metadata[field]):
            violations.append(f"review file has placeholder metadata: {field}: {metadata[field]}")
    reviewer = metadata.get("Reviewer", "")
    producer = metadata.get("Producer", "")
    if reviewer and producer and reviewer.casefold() == producer.casefold():
        violations.append("reviewer must be different from producer")
    reviewer_session = metadata.get("Reviewer-Session", "")
    producer_session = metadata.get("Producer-Session", "")
    if reviewer_session and producer_session and reviewer_session == producer_session:
        violations.append("reviewer session must be different from producer session")
    sections = parse_review_sections(content)
    verdict = str(sections.get("Verdict", "")).strip().lower()
    if verdict not in REVIEW_ALLOWED_VERDICTS:
        violations.append("review verdict must be one of: accept, revise, reject")
    elif verdict != "accept":
        violations.append(f"review verdict must be accept for completion, got: {verdict}")
    for label, allow_none in (("Files", False), ("Findings", True), ("Validation", False), ("Risks", True)):
        violations.extend(list_section_violations(label, list(sections.get(label, [])), allow_none=allow_none))
    if tier == "high-risk" and "Rollback:" not in content:
        violations.append("high-risk review file must include Rollback:")
    if tier == "high-risk":
        violations.extend(list_section_violations("Rollback", list(sections.get("Rollback", [])), allow_none=False))
    return violations


def completion_violations(root: Path, tier: str, review_file: str | None) -> list[str]:
    review_matrix = load_review_matrix(root)
    required_review = review_matrix.get("tiers", {}).get(tier, {}).get("required_review", "none")
    violations = artifact_violations(root, tier)
    if required_review == "none":
        return violations
    resolved_review = resolve_review_file(root, review_file)
    if not resolved_review:
        violations.append("review file is required for this tier")
        return violations
    violations.extend(review_file_violations(root, tier, resolved_review))
    return violations


def command_show(root: Path) -> int:
    runtime = load_runtime(root)
    print(json.dumps(runtime, indent=2, ensure_ascii=False))
    return 0


def command_set_mode(root: Path, mode: str) -> int:
    if mode not in VALID_MODES:
        print(f"invalid mode: {mode}", file=sys.stderr)
        return 2
    runtime = load_runtime(root)
    violations = profile_mode_violations(root, runtime, mode)
    if violations:
        print("BLOCKED")
        for violation in violations:
            print(f"- {violation}")
        return 2
    runtime["mode"] = mode
    save_runtime(root, runtime)
    print(mode)
    return 0


def command_check_start(root: Path, tier: str) -> int:
    activity_bridge.sync(root)
    runtime = load_runtime(root)
    violations = artifact_violations(root, tier)
    return enforce_or_advise(runtime.get("mode", "advisory"), violations)


def command_check_complete(root: Path, tier: str, review_file: str | None) -> int:
    activity_bridge.sync(root)
    runtime = load_runtime(root)
    violations = completion_violations(root, tier, review_file)
    return enforce_or_advise(runtime.get("mode", "advisory"), violations)


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("show")

    set_mode = sub.add_parser("set-mode")
    set_mode.add_argument("mode", choices=sorted(VALID_MODES))

    start = sub.add_parser("check-start")
    start.add_argument("--tier", required=True, choices=["trivial", "normal", "high-risk"])

    complete = sub.add_parser("check-complete")
    complete.add_argument("--tier", required=True, choices=["trivial", "normal", "high-risk"])
    complete.add_argument("--review-file", default=None)

    args = parser.parse_args()
    root = repo_root()

    if args.cmd == "show":
        return command_show(root)
    if args.cmd == "set-mode":
        return command_set_mode(root, args.mode)
    if args.cmd == "check-start":
        return command_check_start(root, args.tier)
    return command_check_complete(root, args.tier, args.review_file)


if __name__ == "__main__":
    raise SystemExit(main())
