#!/usr/bin/env python3
"""Verify that the Codex-native harness skeleton is present and valid."""

from __future__ import annotations

import ast
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]

REQUIRED_DOCS = [
    "AGENTS.md",
    "README.md",
    "ETHOS.md",
    "Design-Options.md",
    "Prompt.md",
    "PRD.md",
    "Plan.md",
    "Implement.md",
    "Documentation.md",
    "Subagent-Manifest.md",
    "Automation-Intent.md",
]

REQUIRED_HOOK_FILES = [
    ".codex/hooks.json",
    ".codex/hooks/README.md",
    ".codex/hooks/session_start.py",
    ".codex/hooks/user_prompt_submit.py",
    ".codex/hooks/post_tool_use.py",
    ".codex/hooks/stop.py",
]

REQUIRED_JSON = [
    ".codex/runtime.json",
]

REQUIRED_MANIFESTS = [
    ".codex/manifests/capability-routing.yaml",
    ".codex/manifests/subagents.yaml",
    ".codex/manifests/review-matrix.yaml",
    ".codex/manifests/mode-policy.yaml",
    ".codex/manifests/automation-policy.yaml",
    ".codex/manifests/evolution-policy.yaml",
]

REQUIRED_PLAYBOOKS = [
    ".codex/playbooks/subagents.md",
    ".codex/playbooks/modes.md",
    ".codex/playbooks/browser-qa.md",
    ".codex/playbooks/computer-use.md",
    ".codex/playbooks/git-ops.md",
    ".codex/playbooks/automations.md",
]

REQUIRED_TEMPLATES = [
    "templates/Prompt.md",
    "templates/PRD.md",
    "templates/Plan.md",
    "templates/Implement.md",
    "templates/Documentation.md",
    "templates/Subagent-Manifest.md",
    "templates/Automation-Intent.md",
    "templates/Design-Options.md",
    "templates/Review.md",
]

REQUIRED_SCRIPTS = [
    "scripts/harness/manifest_loader.py",
    "scripts/harness/session_state.py",
    "scripts/harness/bootstrap.py",
    "scripts/harness/event_log.py",
    "scripts/harness/learning_log.py",
    "scripts/harness/activity_bridge.py",
    "scripts/harness/hook_adapter.py",
    "scripts/harness/runtime_gate.py",
    "scripts/harness/review_gate.py",
    "scripts/harness/protect_paths.py",
    "scripts/harness/append_only_guard.py",
    "scripts/harness/ownership_guard.py",
    "scripts/harness/worktree_manager.py",
    "scripts/harness/validate_manifests.py",
    "scripts/harness/mode_recommender.py",
    "scripts/harness/subagent_planner.py",
    "scripts/harness/automation_planner.py",
    "scripts/harness/review_digest.py",
    "scripts/harness/memory_feedback.py",
    "scripts/harness/skill_auto_gen.py",
    "scripts/harness/insights_report.py",
    "scripts/harness/meta_audit.py",
    "scripts/harness/self_test.py",
]


def check_exists(rel: str) -> tuple[bool, str]:
    path = REPO_ROOT / rel
    return (True, "ok") if path.exists() else (False, "missing")


def check_json(rel: str) -> tuple[bool, str]:
    path = REPO_ROOT / rel
    if not path.exists():
        return False, "missing"
    try:
        json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return False, f"invalid json: {exc}"
    return True, "ok"


def check_script(rel: str) -> tuple[bool, str]:
    path = REPO_ROOT / rel
    if not path.exists():
        return False, "missing"
    try:
        ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError as exc:
        return False, f"syntax error: {exc}"
    return True, "ok"


def main() -> int:
    failures: list[str] = []

    for rel in REQUIRED_DOCS + REQUIRED_HOOK_FILES + REQUIRED_MANIFESTS + REQUIRED_PLAYBOOKS + REQUIRED_TEMPLATES:
        ok, message = check_exists(rel)
        if not ok:
            failures.append(f"{rel}: {message}")

    for rel in REQUIRED_JSON:
        ok, message = check_json(rel)
        if not ok:
            failures.append(f"{rel}: {message}")

    for rel in REQUIRED_SCRIPTS:
        ok, message = check_script(rel)
        if not ok:
            failures.append(f"{rel}: {message}")

    try:
        sys.path.insert(0, str(REPO_ROOT / "scripts" / "harness"))
        from validate_manifests import validate_all

        validate_all(REPO_ROOT)
    except Exception as exc:
        failures.append(f"manifest validation failed: {exc}")

    if failures:
        print("FAILED")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("Harness is live.")
    print(f"checked docs={len(REQUIRED_DOCS)} hooks={len(REQUIRED_HOOK_FILES)} manifests={len(REQUIRED_MANIFESTS)} playbooks={len(REQUIRED_PLAYBOOKS)} templates={len(REQUIRED_TEMPLATES)} scripts={len(REQUIRED_SCRIPTS)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
