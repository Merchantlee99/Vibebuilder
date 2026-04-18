#!/usr/bin/env python3
"""
runtime_gate.py — CLI for flipping runtime.json gate flags.

Usage:
  python3 scripts/harness/runtime_gate.py lock-scope
  python3 scripts/harness/runtime_gate.py review-plan
  python3 scripts/harness/runtime_gate.py verify-tests
  python3 scripts/harness/runtime_gate.py verify-implementation
  python3 scripts/harness/runtime_gate.py verify-deterministic
  python3 scripts/harness/runtime_gate.py approve-ship

Each subcommand flips one flag in runtime.json→gates to true. Also appends
a gate=system event. Only the named flag is changed — monotonic transitions.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


GATE_TRANSITIONS = {
    "lock-scope": "scope_locked",
    "review-plan": "plan_reviewed",
    "verify-tests": "failing_tests_committed",
    "verify-implementation": "implementation_verified",
    "verify-deterministic": "deterministic_verified",
    "approve-ship": "ship_approved",
}


def _find_repo_root(start=None) -> Path:
    current = (Path(start) if start else Path.cwd()).resolve()
    for candidate in (current, *current.parents):
        if (candidate / ".git").exists() or (candidate / ".claude").exists():
            return candidate
    return current


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: runtime_gate.py <subcommand>", file=sys.stderr)
        print(f"available: {', '.join(GATE_TRANSITIONS)}", file=sys.stderr)
        return 2

    cmd = sys.argv[1]
    if cmd not in GATE_TRANSITIONS:
        print(f"unknown: {cmd}. available: {', '.join(GATE_TRANSITIONS)}", file=sys.stderr)
        return 2

    flag = GATE_TRANSITIONS[cmd]
    root = _find_repo_root()
    rt_path = root / ".claude" / "runtime.json"
    if not rt_path.exists():
        print(f"runtime.json not found at {rt_path}", file=sys.stderr)
        return 2

    rt = json.loads(rt_path.read_text(encoding="utf-8"))
    gates = rt.setdefault("gates", {})
    was = gates.get(flag, False)
    gates[flag] = True
    rt_path.write_text(json.dumps(rt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"{flag}: {was} → True")

    # record event
    sys.path.insert(0, str(root / "scripts" / "harness"))
    try:
        import event_log
        event_log.append_event(
            gate="system", outcome="runtime-gate-flipped", actor="user",
            file_path=".claude/runtime.json",
            detail={"flag": flag, "subcommand": cmd, "previous": was}, repo_root=root,
        )
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
