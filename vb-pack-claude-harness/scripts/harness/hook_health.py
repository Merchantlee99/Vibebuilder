#!/usr/bin/env python3
"""
hook_health.py — Circuit breaker for Claude Code hooks.

Tracks per-hook failure streaks in .claude/runtime.json → hook_health.
When a hook fails (exit != 0, timeout, or exception) ≥ 3 times in a row,
it is marked `disabled: true` and a pending note appears in
.claude/audits/hook-breaker-<ts>.md.

Subsequent hook invocations check the disabled flag first and exit 0
(pass-through) until the user manually re-enables by setting
  runtime.json → hook_health.<hook>.disabled = false
  runtime.json → hook_health.<hook>.streak = 0

Usage (from inside each hook, at the top of main()):

    from hook_health import circuit_check, record_success, record_failure

    disabled, reason = circuit_check("pre_tool_use", repo_root)
    if disabled:
        # fall through — do not block, do not do work
        sys.stdout.write(json.dumps({"systemMessage": reason}) + "\\n")
        sys.exit(0)

    try:
        ...  # hook body
        record_success("pre_tool_use", repo_root)
    except Exception as exc:
        record_failure("pre_tool_use", repo_root, reason=str(exc))
        raise

CLI:
  python3 scripts/harness/hook_health.py status
  python3 scripts/harness/hook_health.py reset <hook-name>
  python3 scripts/harness/hook_health.py disable <hook-name>
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path
from typing import Optional


STREAK_THRESHOLD = 3  # consecutive failures → auto-disable
HOOK_NAMES = {
    "session_start", "user_prompt_submit",
    "pre_tool_use", "post_tool_use", "stop",
    "gate_4_runner",
}


def _find_root(start: Optional[Path] = None) -> Path:
    current = (start or Path.cwd()).resolve()
    for candidate in (current, *current.parents):
        if (candidate / ".git").exists() or (candidate / ".claude").exists():
            return candidate
    return current


def _load_runtime(repo_root: Path) -> dict:
    path = repo_root / ".claude" / "runtime.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _save_runtime(repo_root: Path, runtime: dict) -> None:
    path = repo_root / ".claude" / "runtime.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(runtime, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8")


def _get_health(runtime: dict) -> dict:
    return runtime.setdefault("hook_health", {})


def _get_hook_state(health: dict, hook_name: str) -> dict:
    return health.setdefault(hook_name, {
        "streak": 0,
        "disabled": False,
        "last_failure_ts": "",
        "last_failure_reason": "",
        "last_success_ts": "",
    })


def circuit_check(hook_name: str, repo_root: Optional[Path] = None) -> tuple[bool, str]:
    """Return (is_disabled, reason).

    If True, caller should skip the hook body and exit 0.
    """
    root = repo_root or _find_root()
    runtime = _load_runtime(root)
    health = runtime.get("hook_health", {})
    state = health.get(hook_name, {})
    disabled = bool(state.get("disabled", False))
    if not disabled:
        return False, ""
    reason = (
        f"hook '{hook_name}' disabled by circuit breaker "
        f"(streak={state.get('streak', 0)}, last_reason={state.get('last_failure_reason', '')}). "
        f"Re-enable: python3 scripts/harness/hook_health.py reset {hook_name}"
    )
    return True, reason


def record_success(hook_name: str, repo_root: Optional[Path] = None) -> None:
    root = repo_root or _find_root()
    runtime = _load_runtime(root)
    health = _get_health(runtime)
    state = _get_hook_state(health, hook_name)
    state["streak"] = 0
    state["last_success_ts"] = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    # Note: we do NOT auto-re-enable a disabled hook on a single success.
    # User must explicitly reset via CLI.
    _save_runtime(root, runtime)


def record_failure(hook_name: str, repo_root: Optional[Path] = None,
                   reason: str = "") -> None:
    root = repo_root or _find_root()
    runtime = _load_runtime(root)
    health = _get_health(runtime)
    state = _get_hook_state(health, hook_name)
    state["streak"] = int(state.get("streak", 0)) + 1
    state["last_failure_ts"] = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    state["last_failure_reason"] = (reason or "")[:400]

    if state["streak"] >= STREAK_THRESHOLD and not state.get("disabled"):
        state["disabled"] = True
        # Write a pending audit note
        audits = root / ".claude" / "audits"
        audits.mkdir(parents=True, exist_ok=True)
        stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        note = audits / f"hook-breaker-{hook_name}-{stamp}.md"
        note.write_text(
            f"# Circuit breaker tripped — {hook_name}\n\n"
            f"Triggered at {stamp}.\n\n"
            f"- Consecutive failures: {state['streak']}\n"
            f"- Last reason: {state['last_failure_reason']}\n\n"
            f"## Recovery\n\n"
            f"1. Investigate the hook: `.claude/hooks/{hook_name}.py`\n"
            f"2. Check recent events.jsonl entries for clues\n"
            f"3. Fix the root cause\n"
            f"4. Re-enable: `python3 scripts/harness/hook_health.py reset {hook_name}`\n"
            f"\n"
            f"Until reset, this hook passes through (exit 0) without running.\n",
            encoding="utf-8",
        )
        # Record event
        try:
            sys.path.insert(0, str(root / "scripts" / "harness"))
            import event_log  # type: ignore
            event_log.append_event(
                gate="system", outcome="hook-circuit-tripped", actor="system",
                file_path=str(note.relative_to(root)),
                detail={"hook": hook_name, "streak": state["streak"],
                        "reason": state["last_failure_reason"]},
                repo_root=root,
            )
        except Exception:
            pass

    _save_runtime(root, runtime)


def _cmd_status(repo_root: Path) -> int:
    runtime = _load_runtime(repo_root)
    health = runtime.get("hook_health", {})
    if not health:
        print("(no hook health data yet)")
        return 0
    for name in sorted(HOOK_NAMES | set(health.keys())):
        s = health.get(name, {})
        status = "DISABLED" if s.get("disabled") else "ok"
        print(f"  {name:<24} {status:<10} streak={s.get('streak', 0)}  "
              f"last_success={s.get('last_success_ts', '-')}  "
              f"last_fail={s.get('last_failure_ts', '-')}")
    return 0


def _cmd_reset(repo_root: Path, hook_name: str) -> int:
    if hook_name not in HOOK_NAMES:
        print(f"unknown hook: {hook_name} (known: {sorted(HOOK_NAMES)})", file=sys.stderr)
        return 2
    runtime = _load_runtime(repo_root)
    health = _get_health(runtime)
    state = _get_hook_state(health, hook_name)
    was_disabled = state.get("disabled", False)
    state["streak"] = 0
    state["disabled"] = False
    _save_runtime(repo_root, runtime)
    print(f"reset: {hook_name} (was disabled={was_disabled})")
    return 0


def _cmd_disable(repo_root: Path, hook_name: str) -> int:
    if hook_name not in HOOK_NAMES:
        print(f"unknown hook: {hook_name} (known: {sorted(HOOK_NAMES)})", file=sys.stderr)
        return 2
    runtime = _load_runtime(repo_root)
    health = _get_health(runtime)
    state = _get_hook_state(health, hook_name)
    state["disabled"] = True
    state["last_failure_reason"] = "manually disabled"
    _save_runtime(repo_root, runtime)
    print(f"disabled: {hook_name}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=("status", "reset", "disable"))
    ap.add_argument("hook_name", nargs="?")
    args = ap.parse_args()
    root = _find_root()
    if args.cmd == "status":
        return _cmd_status(root)
    if args.cmd == "reset":
        if not args.hook_name:
            print("usage: hook_health.py reset <hook-name>", file=sys.stderr)
            return 2
        return _cmd_reset(root, args.hook_name)
    if args.cmd == "disable":
        if not args.hook_name:
            print("usage: hook_health.py disable <hook-name>", file=sys.stderr)
            return 2
        return _cmd_disable(root, args.hook_name)
    return 2


if __name__ == "__main__":
    sys.exit(main())
