#!/usr/bin/env python3
"""Optional Codex Stop hook for enforced-mode completion continuation."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RUNTIME = ROOT / "harness" / "runtime.json"


def main() -> int:
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError:
        payload = {}

    if payload.get("stop_hook_active"):
        return 0

    try:
        runtime = json.loads(RUNTIME.read_text(encoding="utf-8"))
    except Exception:
        return 0

    if runtime.get("enforcement_mode") != "enforced":
        return 0

    proc = subprocess.run(
        [sys.executable, "scripts/harness/session_close.py", "--tier", runtime.get("default_tier", "normal")],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode == 0:
        return 0

    reason = "Harness finish gate failed. Continue the turn, fix or report these blockers:\n"
    reason += (proc.stdout + "\n" + proc.stderr).strip()
    print(json.dumps({"decision": "block", "reason": reason}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
