#!/usr/bin/env python3
"""
review_matrix_policy.py — Layer 2: reads agents/review-matrix.json
and decides which reviewers are required for the current stage.

Exported:
  required_reviewers_for_stage(stage) → list[role_id]
  stage_max_parallel(stage) → int
  current_stage_from_runtime(runtime) → str
  next_stage(runtime) → str | None

TODO(v1):
  - parallel reviewer dispatch (currently serial)
  - conditional reviewers based on tier × complexity
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


MATRIX_PATH = ".claude/agents/review-matrix.json"


def _find_root(start=None) -> Path:
    current = (Path(start) if start else Path.cwd()).resolve()
    for candidate in (current, *current.parents):
        if (candidate / ".git").exists() or (candidate / ".claude").exists():
            return candidate
    return current


def _load_matrix(repo_root: Path) -> dict:
    path = repo_root / MATRIX_PATH
    if not path.exists():
        return {"stages": []}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"stages": []}


def required_reviewers_for_stage(stage: str, repo_root: Path | None = None) -> list[str]:
    root = repo_root or _find_root()
    matrix = _load_matrix(root)
    for s in matrix.get("stages", []):
        if s.get("name") == stage:
            return list(s.get("required_reviewers", []))
    return []


def stage_max_parallel(stage: str, repo_root: Path | None = None) -> int:
    root = repo_root or _find_root()
    matrix = _load_matrix(root)
    default = (matrix.get("dispatch", {}) or {}).get("default_max_parallel", 2)
    for s in matrix.get("stages", []):
        if s.get("name") == stage:
            return int(s.get("max_parallel", default))
    return default


def current_stage_from_runtime(runtime: dict) -> str:
    """Derive current stage from runtime.gates flags."""
    gates = runtime.get("gates", {}) or {}
    if not gates.get("scope_locked"):
        return "plan"
    if not gates.get("plan_reviewed"):
        return "plan"
    if not gates.get("failing_tests_committed"):
        return "tests"
    if not gates.get("implementation_verified"):
        return "implementation"
    if not gates.get("deterministic_verified"):
        return "verification"
    if not gates.get("ship_approved"):
        return "postmortem"
    return "done"


def next_stage(runtime: dict) -> str | None:
    order = ["plan", "tests", "implementation", "verification", "postmortem", "done"]
    cur = current_stage_from_runtime(runtime)
    try:
        idx = order.index(cur)
        return order[idx + 1] if idx + 1 < len(order) else None
    except ValueError:
        return None
