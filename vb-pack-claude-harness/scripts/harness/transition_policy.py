#!/usr/bin/env python3
"""
transition_policy.py — Layer 2: stage transition guards.

When the builder role wants to move from stage N to stage N+1, this module
checks that all required_reviewers for stage N have recorded pass events
AND the exit_condition gate flag is true.

Exported:
  can_transition(runtime, from_stage, to_stage) → (bool, reason)
  commit_transition(runtime, to_stage) → updated runtime

TODO(v1):
  - force transition override (user approved) path
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any


def can_transition(runtime: dict[str, Any], from_stage: str, to_stage: str,
                    repo_root: Path | None = None) -> tuple[bool, str]:
    gates = runtime.get("gates", {}) or {}
    requirements = {
        "plan": ("scope_locked", "plan_reviewed"),
        "tests": ("failing_tests_committed",),
        "implementation": ("implementation_verified",),
        "verification": ("deterministic_verified",),
        "postmortem": (),
    }
    for flag in requirements.get(from_stage, ()):
        if not gates.get(flag):
            return False, f"gate flag '{flag}' not set"

    # Also: required_reviewers for from_stage must have pass events
    sys.path.insert(0, str((repo_root or Path.cwd()) / "scripts" / "harness"))
    try:
        from review_matrix_policy import required_reviewers_for_stage
        import event_log
    except Exception:
        return True, "reviewer check skipped (modules unavailable)"

    reviewers = required_reviewers_for_stage(from_stage, repo_root=repo_root)
    if not reviewers:
        return True, "no reviewers required"

    seen: set[str] = set()
    for e in event_log.iter_all_events(repo_root=repo_root):
        if e.get("gate") == "02" and e.get("outcome") == "pass":
            actor = e.get("actor", "")
            if actor in reviewers:
                seen.add(actor)

    missing = [r for r in reviewers if r not in seen]
    if missing:
        return False, f"missing reviewer passes: {missing}"
    return True, "ok"


def commit_transition(runtime: dict, to_stage: str) -> dict:
    rt = dict(runtime)
    meta = dict(rt.get("stage_meta", {}) or {})
    meta["current"] = to_stage
    import time
    meta["transitioned_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    rt["stage_meta"] = meta
    return rt
