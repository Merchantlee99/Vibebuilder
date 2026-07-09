#!/usr/bin/env python3
"""Run GPT-5.6 Codex Skill Router local self-checks."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"


def run(cmd: list[str]) -> dict[str, object]:
    result = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True)
    return {
        "cmd": cmd,
        "returncode": result.returncode,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
    }


def main() -> int:
    checks = [
        run(["python3", "-m", "py_compile", *[str(path) for path in sorted(SCRIPTS.glob("*.py"))]]),
        run(["python3", str(SCRIPTS / "route_eval.py"), "--suite", "train"]),
        run(["python3", str(SCRIPTS / "route_eval.py"), "--suite", "heldout"]),
    ]
    failed = [check for check in checks if check["returncode"] != 0]
    report = {"root": str(ROOT), "passed": len(checks) - len(failed), "failed": len(failed), "checks": checks}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
