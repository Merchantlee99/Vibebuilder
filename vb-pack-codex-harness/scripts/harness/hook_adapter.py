#!/usr/bin/env python3
"""Shared logic for repo-local Codex hook adapters."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    import activity_bridge
    import memory_feedback
    import runtime_gate
    import session_state
else:  # pragma: no cover - package import path
    from . import activity_bridge, memory_feedback, runtime_gate, session_state


def repo_root_from(path: str | None = None) -> Path | None:
    current = Path(path or Path.cwd()).resolve()
    for candidate in (current, *current.parents):
        if (candidate / ".codex" / "runtime.json").exists():
            return candidate
    return None


def load_runtime(root: Path) -> dict[str, Any]:
    try:
        return json.loads((root / ".codex" / "runtime.json").read_text(encoding="utf-8"))
    except Exception:
        return {}


def hook_settings(root: Path) -> dict[str, Any]:
    settings = load_runtime(root).get("hook_adapter", {})
    return settings if isinstance(settings, dict) else {}


def hooks_enabled(root: Path) -> bool:
    return bool(hook_settings(root).get("enabled", False))


def load_payload(raw: str) -> dict[str, Any]:
    if not raw.strip():
        return {}
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _context_prefix(root: Path) -> str:
    runtime = load_runtime(root)
    profile = runtime.get("deployment_profile", "template")
    mode = runtime.get("mode", "advisory")
    stage = runtime.get("stage", "unknown")
    return f"Codex harness active. profile={profile}, mode={mode}, stage={stage}."


def session_start_output(root: Path, payload: dict[str, Any]) -> dict[str, Any] | None:
    if not hooks_enabled(root):
        return None
    activity_bridge.sync(root)
    session_state.resolve_session_id(root)
    additional = (
        _context_prefix(root)
        + " For normal/high-risk work, keep Prompt.md/PRD.md/Plan.md/Implement.md/Documentation.md in sync, use review_gate.py prepare/finalize before completion, generate subagent dispatch with subagent_planner.py, and scan follow-up continuity with automation_planner.py."
    )
    return {
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": additional,
        }
    }


def user_prompt_submit_output(root: Path, payload: dict[str, Any]) -> dict[str, Any] | None:
    if not hooks_enabled(root):
        return None
    settings = hook_settings(root)
    if not settings.get("prefetch_on_prompt", True):
        return None
    prompt = str(payload.get("prompt", "") or "")
    if not prompt.strip():
        return None
    activity_bridge.sync(root)
    top_k = int(settings.get("prefetch_top_k", 3) or 3)
    prefetched = memory_feedback.prefetch(prompt, top_k, root)
    if not prefetched.strip():
        return None
    additional = "Relevant harness learnings:\n" + prefetched
    return {
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": additional,
        }
    }


def _tier_from_plan(root: Path) -> str:
    plan = root / "Plan.md"
    if not plan.exists():
        return ""
    for raw_line in plan.read_text(encoding="utf-8").splitlines():
        stripped = raw_line.strip().lower()
        if stripped.startswith("- tier:"):
            return stripped.split(":", 1)[1].strip()
    return ""


def stop_output(root: Path, payload: dict[str, Any]) -> dict[str, Any] | None:
    if not hooks_enabled(root):
        return None
    settings = hook_settings(root)
    if not settings.get("stop_on_pending_review", True):
        return None
    if payload.get("stop_hook_active"):
        return None
    runtime = load_runtime(root)
    if runtime.get("deployment_profile") != "project":
        return None
    tier = _tier_from_plan(root)
    if tier not in {"normal", "high-risk"}:
        return None
    resolved = runtime_gate.resolve_review_file(root, "latest")
    if not resolved:
        return None
    violations = runtime_gate.completion_violations(root, tier, resolved)
    review_violations = [
        item
        for item in violations
        if item.startswith("review")
        or "verdict" in item.lower()
        or "placeholder" in item.lower()
    ]
    if not review_violations:
        return None
    return {
        "decision": "block",
        "reason": (
            f"Review gate is still open for {tier} work. Complete {resolved} and run "
            f"`python3 scripts/harness/review_gate.py finalize --tier {tier} --review-file latest` before concluding."
        ),
    }


def post_tool_use_output(root: Path, payload: dict[str, Any]) -> dict[str, Any] | None:
    if not hooks_enabled(root):
        return None
    settings = hook_settings(root)
    if not settings.get("post_tool_sync", True):
        return None
    changed = activity_bridge.sync(root)
    if not changed:
        return None
    command = str((payload.get("tool_input") or {}).get("command", "") or "")
    additional = (
        f"Filesystem sync captured {len(changed)} changed artifact(s) after Bash."
        + (f" Last command: `{command}`." if command else "")
    )
    return {
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": additional,
        }
    }
