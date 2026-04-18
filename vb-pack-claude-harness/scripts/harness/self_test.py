#!/usr/bin/env python3
"""
self_test.py — Verify all 10 gates + harness scripts + 4-axis files are
live, executable, syntactically valid, and correctly registered.

Run this after bootstrapping a new project:

    python3 scripts/harness/self_test.py

Exit 0 = all green. Exit 1 = one or more problems.
"""

from __future__ import annotations

import ast
import json
import stat
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


EXPECTED_HOOKS = {
    "session_start.py":    {"SessionStart"},
    "user_prompt_submit.py": {"UserPromptSubmit"},
    "pre_tool_use.py":     {"PreToolUse"},
    "post_tool_use.py":    {"PostToolUse"},
    "stop.py":             {"Stop"},
}

EXPECTED_HARNESS_SCRIPTS = [
    "event_log.py",
    "learning_log.py",
    "size_check.py",
    "bash_write_probe.py",
    "rotate_logs.py",
    "meta_supervisor.py",
    "memory_manager.py",
    "skill_auto_gen.py",
    "taxonomy_learner.py",
    "insights_engine.py",
    "session_index.py",
    "oversight_policy.py",
    "risk_policy.py",
    "review_matrix_policy.py",
    "transition_policy.py",
    "runtime_gate.py",
    "hook_health.py",
    "self_test.py",
    "bootstrap.py",
    "invoke_reviewer.py",
    "append_only_lock.py",
    "subagent_planner.py",
    "automation_planner.py",
    "mcp_audit.py",
    "activity_replay.py",
    "protected_paths.py",
]

EXPECTED_CORE_DOCS = [
    "README.md", "CLAUDE.md", "AGENTS.md", "ETHOS.md",
]

EXPECTED_CORE_FILES = [
    ".claude/settings.local.json",
    ".claude/runtime.json",
    ".claude/known-gaps.md",
    ".claude/agents/manifest.json",
    ".claude/agents/review-matrix.json",
]

EXPECTED_SEALED_PROMPTS = [
    "direction-check.md",
    "review-code.md",
    "review-plan.md",
    "planner.md",
    "plan-redteam.md",
    "implement-tests.md",
    "implement-code.md",
    "tests-redteam.md",
    "diff-redteam.md",
    "risk-reviewer.md",
    "verifier.md",
    "failure-analysis.md",
    "meta-audit.md",
]


def check_hook(name: str) -> tuple[bool, str]:
    path = REPO_ROOT / ".claude" / "hooks" / name
    if not path.exists():
        return False, "missing"
    mode = path.stat().st_mode
    if not (mode & stat.S_IXUSR):
        return False, "not executable (run: chmod +x)"
    try:
        ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError as exc:
        return False, f"syntax error: {exc}"
    return True, "ok"


def check_script(name: str) -> tuple[bool, str]:
    path = REPO_ROOT / "scripts" / "harness" / name
    if not path.exists():
        return False, "missing"
    try:
        ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError as exc:
        return False, f"syntax error: {exc}"
    return True, "ok"


def check_file(rel: str) -> tuple[bool, str]:
    path = REPO_ROOT / rel
    if not path.exists():
        return False, "missing"
    if rel.endswith(".json"):
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            return False, f"invalid JSON: {exc}"
    return True, "ok"


def check_sealed_prompt(name: str) -> tuple[bool, str]:
    path = REPO_ROOT / ".claude" / "sealed-prompts" / name
    if not path.exists():
        return False, "missing"
    size = path.stat().st_size
    if size < 200:
        return False, f"too small ({size}B)"
    return True, "ok"


def load_hook_registrations() -> dict[str, set[str]]:
    path = REPO_ROOT / ".claude" / "settings.local.json"
    if not path.exists():
        return {}
    try:
        cfg = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    out: dict[str, set[str]] = {}
    for event_name, entries in (cfg.get("hooks") or {}).items():
        for entry in entries:
            for hook in entry.get("hooks", []):
                cmd = hook.get("command", "")
                for expected in EXPECTED_HOOKS:
                    if expected in cmd:
                        out.setdefault(expected, set()).add(event_name)
    return out


def main() -> int:
    failures: list[str] = []

    print("== Hooks ==")
    registrations = load_hook_registrations()
    for name, expected_events in EXPECTED_HOOKS.items():
        ok, why = check_hook(name)
        got_events = registrations.get(name, set())
        reg_ok = expected_events.issubset(got_events)
        status = "active" if (ok and reg_ok) else "INACTIVE"
        print(f"  {name:<25} {status:<10} file={why}  registered={sorted(got_events) or '(none)'}")
        if not ok:
            failures.append(f"hook {name}: {why}")
        if not reg_ok:
            missing = expected_events - got_events
            failures.append(f"hook {name}: not registered under {sorted(missing)}")

    print()
    print("== Harness scripts ==")
    for name in EXPECTED_HARNESS_SCRIPTS:
        ok, why = check_script(name)
        print(f"  scripts/harness/{name:<30} {'ok' if ok else 'FAIL':<6}  {why}")
        if not ok:
            failures.append(f"script {name}: {why}")

    print()
    print("== Core docs ==")
    for name in EXPECTED_CORE_DOCS:
        ok, why = check_file(name)
        print(f"  {name:<15} {'ok' if ok else 'FAIL':<6}  {why}")
        if not ok:
            failures.append(f"doc {name}: {why}")

    print()
    print("== Core files ==")
    for rel in EXPECTED_CORE_FILES:
        ok, why = check_file(rel)
        print(f"  {rel:<40} {'ok' if ok else 'FAIL':<6}  {why}")
        if not ok:
            failures.append(f"file {rel}: {why}")

    print()
    print("== Sealed prompts ==")
    for name in EXPECTED_SEALED_PROMPTS:
        ok, why = check_sealed_prompt(name)
        print(f"  sealed-prompts/{name:<30} {'ok' if ok else 'FAIL':<6}  {why}")
        if not ok:
            failures.append(f"sealed-prompt {name}: {why}")

    print()
    if failures:
        print(f"FAILED ({len(failures)} problem(s)):")
        for f in failures:
            print(f"  - {f}")
        return 1
    print(f"All {len(EXPECTED_HOOKS)} hooks + {len(EXPECTED_HARNESS_SCRIPTS)} harness scripts + "
          f"{len(EXPECTED_CORE_DOCS)} docs + {len(EXPECTED_CORE_FILES)} core files + "
          f"{len(EXPECTED_SEALED_PROMPTS)} sealed prompts verified.")
    print("Harness is live.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
