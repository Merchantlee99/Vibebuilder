#!/usr/bin/env python3
"""Run completion checks before Codex reports final completion."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys

from common import ROOT


def run(command: list[str]) -> tuple[bool, str]:
    proc = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)
    output = (proc.stdout + proc.stderr).strip()
    return proc.returncode == 0, output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tier", choices=["trivial", "normal", "high-risk"], default="normal")
    parser.add_argument("--artifact-dir", default="docs/ai/current")
    parser.add_argument("--review-file")
    parser.add_argument("--template", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    commands = [
        ["scripts/harness/gate.py", "finish-gate", "--tier", args.tier, "--artifact-dir", args.artifact_dir],
        ["scripts/harness/subagent_planner.py", "check", "--quiet"],
        ["scripts/harness/automation_planner.py", "audit"],
        ["scripts/harness/skillify_audit.py", "all"],
    ]
    if args.template:
        commands[0].append("--template")
    if args.review_file:
        commands[0].extend(["--review-file", args.review_file])

    results = []
    ok = True
    for command in commands:
        success, output = run([sys.executable, *command])
        ok = ok and success
        results.append({"command": " ".join(command), "ok": success, "output": output})

    if args.json:
        print(json.dumps({"ok": ok, "results": results}, indent=2))
    else:
        for result in results:
            status = "PASS" if result["ok"] else "FAIL"
            print(f"{status}: {result['command']}")
            if result["output"]:
                print(result["output"])
        print("session close ok" if ok else "session close blocked")

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

