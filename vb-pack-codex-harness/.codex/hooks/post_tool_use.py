#!/usr/bin/env python3
"""Repo-local Codex PostToolUse hook adapter."""

from __future__ import annotations

import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "harness"))

import hook_adapter  # noqa: E402


def main() -> int:
    payload = hook_adapter.load_payload(sys.stdin.read())
    result = hook_adapter.post_tool_use_output(REPO_ROOT, payload)
    if result:
        print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
