#!/usr/bin/env python3
"""Optional Codex PreToolUse guard for dangerous shell commands."""

from __future__ import annotations

import json
import re
import sys


BLOCK_PATTERNS = [
    r"\brm\s+-rf\s+/",
    r"\bgit\s+reset\s+--hard\b",
    r"\bgit\s+checkout\s+--\b",
    r"\bgit\s+clean\s+-fd",
    r"\bsudo\s+rm\b",
    r"\bchmod\s+-R\s+777\b",
]


def main() -> int:
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError:
        return 0

    command = (
        payload.get("tool_input", {}).get("command")
        or payload.get("command")
        or ""
    )

    for pattern in BLOCK_PATTERNS:
        if re.search(pattern, command):
            print(json.dumps({
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": "Blocked by Codex Harness command policy."
                }
            }))
            return 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

