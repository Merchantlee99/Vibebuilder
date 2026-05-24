#!/usr/bin/env python3
"""Optional Codex UserPromptSubmit hook that injects concise harness context."""

from __future__ import annotations

import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
RUNTIME = ROOT / "harness" / "runtime.json"


def main() -> int:
    runtime = {}
    if RUNTIME.exists():
        try:
            runtime = json.loads(RUNTIME.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            runtime = {}

    context = (
        "Codex Harness active. Classify the task tier before meaningful edits. "
        "For normal/high-risk work, use plan, validation, independent review, "
        "and explicit subagent write scopes when delegating. "
        f"Profile={runtime.get('deployment_profile', 'unknown')} "
        f"mode={runtime.get('enforcement_mode', 'unknown')}."
    )

    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": context
        }
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

