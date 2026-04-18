#!/usr/bin/env python3
"""Generate automation intent suggestions from harness state."""

from __future__ import annotations

import argparse
import calendar
import json
import sys
import time
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import activity_bridge
    import event_log
    import learning_log
    import runtime_gate
    from manifest_loader import load as load_manifest
else:  # pragma: no cover - package import path
    from . import activity_bridge, event_log, learning_log, runtime_gate
    from .manifest_loader import load as load_manifest


STATE_PATH = Path(".codex/context/automation-intents.json")


def repo_root() -> Path:
    return event_log.repo_root()


def load_policy(root: Path) -> dict[str, Any]:
    path = root / ".codex" / "manifests" / "automation-policy.yaml"
    if not path.exists():
        return {}
    return load_manifest(path)


def load_runtime(root: Path) -> dict[str, Any]:
    path = root / ".codex" / "runtime.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def state_path(root: Path) -> Path:
    return root / STATE_PATH


def load_state(root: Path) -> dict[str, Any]:
    path = state_path(root)
    if not path.exists():
        return {"generated_at": "", "suggestions": []}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"generated_at": "", "suggestions": []}
    suggestions = payload.get("suggestions", [])
    if not isinstance(suggestions, list):
        suggestions = []
    return {
        "generated_at": str(payload.get("generated_at", "")),
        "suggestions": suggestions,
    }


def save_state(root: Path, payload: dict[str, Any]) -> Path:
    path = state_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def parse_ts(raw: str) -> float | None:
    try:
        return float(calendar.timegm(time.strptime(raw, "%Y-%m-%dT%H:%M:%SZ")))
    except Exception:
        return None


def plan_tier(root: Path) -> str:
    path = root / "Plan.md"
    if not path.exists():
        return "normal"
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        stripped = raw_line.strip().lower()
        if stripped.startswith("- tier:"):
            value = stripped.split(":", 1)[1].strip()
            if value:
                return value
    return "normal"


def latest_insights_report(root: Path) -> Path | None:
    candidates = sorted(
        path for path in (root / ".codex" / "audits").glob("insights-*.md") if path.is_file()
    )
    return candidates[-1] if candidates else None


def proposed_skill_paths(root: Path) -> list[Path]:
    return sorted(
        path
        for path in (root / ".codex" / "skills" / "_proposed").glob("*.md")
        if path.name.lower() != "readme.md"
    )


def policy_loop(policy: dict[str, Any], key: str) -> dict[str, Any]:
    loops = policy.get("recommended_loops", {})
    if isinstance(loops, dict):
        payload = loops.get(key, {})
        if isinstance(payload, dict):
            return payload
    return {}


def build_suggestion(
    *,
    policy: dict[str, Any],
    key: str,
    name: str,
    prompt: str,
    evidence: dict[str, Any],
) -> dict[str, Any]:
    defaults = policy.get("defaults", {})
    loop = policy_loop(policy, key)
    kind = str(loop.get("kind", defaults.get("kind", "heartbeat")) or "heartbeat")
    destination = str(loop.get("destination", defaults.get("destination", "thread")) or "thread")
    cadence_hint = str(loop.get("cadence_hint", "weekly") or "weekly")
    skip_condition = str(loop.get("skip_condition", "none") or "none")
    expected_output = str(loop.get("expected_output", "short status update") or "short status update")
    return {
        "name": name,
        "signal": key,
        "kind": kind,
        "destination": destination,
        "cadence_hint": cadence_hint,
        "prompt": prompt,
        "skip_condition": skip_condition,
        "expected_output": expected_output,
        "evidence": evidence,
    }


def pending_review_suggestion(root: Path, policy: dict[str, Any]) -> dict[str, Any] | None:
    review_file = runtime_gate.resolve_review_file(root, "latest")
    if not review_file:
        return None
    tier = plan_tier(root)
    violations = runtime_gate.review_file_violations(root, tier, review_file)
    if not violations:
        return None
    prompt = (
        "Inspect the latest review artifact, resolve each open review-gate issue, and either complete "
        "`python3 scripts/harness/review_gate.py finalize --tier "
        f"{tier} --review-file latest` or record the blocking reason with exact file references."
    )
    return build_suggestion(
        policy=policy,
        key="pending_review_followup",
        name="Pending Review Follow-up",
        prompt=prompt,
        evidence={
            "review_file": review_file,
            "tier": tier,
            "violation_count": len(violations),
            "violations": violations[:8],
        },
    )


def insights_suggestion(root: Path, policy: dict[str, Any], runtime: dict[str, Any]) -> dict[str, Any] | None:
    reports_path = latest_insights_report(root)
    events = list(event_log.iter_events(root) or [])
    learnings = learning_log.load_recent(limit=1000, root=root)
    proposals = proposed_skill_paths(root)
    if not events and not learnings and not proposals:
        return None

    interval_days = int((runtime.get("feedback_loop", {}) or {}).get("insights_interval_days", 7) or 7)
    now = time.time()
    if reports_path is None:
        reason = "no insights report exists yet"
        new_events = len(events)
        new_learnings = len(learnings)
    else:
        age_days = (now - reports_path.stat().st_mtime) / 86400
        report_cutoff = reports_path.stat().st_mtime
        new_events = sum(1 for item in events if (parse_ts(str(item.get("ts", ""))) or 0) > report_cutoff)
        new_learnings = sum(1 for item in learnings if (parse_ts(str(item.get("ts", ""))) or 0) > report_cutoff)
        if age_days < interval_days and new_events == 0 and new_learnings == 0 and not proposals:
            return None
        reason = f"insights report is stale or new activity accumulated (interval={interval_days}d)"

    prompt = (
        "Run `python3 scripts/harness/memory_feedback.py sync-from-events`, "
        "`python3 scripts/harness/skill_auto_gen.py`, and `python3 scripts/harness/insights_report.py`. "
        "Then summarize the top repeated failure patterns, proposed skills, and one concrete harness adjustment."
    )
    return build_suggestion(
        policy=policy,
        key="harness_evolution_sweep",
        name="Harness Evolution Sweep",
        prompt=prompt,
        evidence={
            "reason": reason,
            "event_count": len(events),
            "learning_count": len(learnings),
            "proposed_skill_count": len(proposals),
            "latest_report": str(reports_path.relative_to(root)) if reports_path else "none",
            "new_events_since_report": new_events,
            "new_learnings_since_report": new_learnings,
        },
    )


def proposed_skill_suggestion(root: Path, policy: dict[str, Any]) -> dict[str, Any] | None:
    proposals = proposed_skill_paths(root)
    if not proposals:
        return None
    prompt = (
        "Review proposed skills under `.codex/skills/_proposed/`, decide whether each item should be promoted, "
        "revised, or archived, and capture the required edits or open questions."
    )
    return build_suggestion(
        policy=policy,
        key="proposed_skill_triage",
        name="Proposed Skill Triage",
        prompt=prompt,
        evidence={
            "proposal_count": len(proposals),
            "files": [str(path.relative_to(root)) for path in proposals[:10]],
        },
    )


def scan(root: Path) -> dict[str, Any]:
    activity_bridge.sync(root)
    policy = load_policy(root)
    runtime = load_runtime(root)
    suggestions = [
        item
        for item in (
            pending_review_suggestion(root, policy),
            insights_suggestion(root, policy, runtime),
            proposed_skill_suggestion(root, policy),
        )
        if item is not None
    ]
    payload = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "suggestions": suggestions,
    }
    save_state(root, payload)
    if suggestions:
        event_log.append_event(
            kind="automation-intent",
            actor="orchestrator",
            summary=f"generated {len(suggestions)} automation suggestion(s)",
            stage="planning",
            detail={"signals": [item["signal"] for item in suggestions]},
            root=root,
        )
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("scan")
    sub.add_parser("show")
    args = parser.parse_args()

    root = repo_root()
    if args.cmd == "scan":
        print(json.dumps(scan(root), indent=2, ensure_ascii=False))
        return 0
    print(json.dumps(load_state(root), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
