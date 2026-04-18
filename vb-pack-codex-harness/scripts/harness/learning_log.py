#!/usr/bin/env python3
"""Append-only learning log for recurring mistakes and fixes."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any


LOG_DIR = Path(".codex/telemetry")
LOG_FILE = "learnings.jsonl"


def repo_root() -> Path:
    current = Path.cwd().resolve()
    for candidate in (current, *current.parents):
        if (candidate / ".codex").exists() or (candidate / ".git").exists():
            return candidate
    return current


def log_path(root: Path | None = None) -> Path:
    base = root or repo_root()
    return base / LOG_DIR / LOG_FILE


def append_learning(
    *,
    pattern: str,
    mistake: str,
    fix: str,
    actor: str = "system",
    context: dict[str, Any] | None = None,
    root: Path | None = None,
) -> Path:
    path = log_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "pattern": pattern,
        "mistake": mistake,
        "fix": fix,
        "actor": actor,
        "context": context or {},
    }
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    return path


def load_recent(limit: int = 20, root: Path | None = None) -> list[dict[str, Any]]:
    path = log_path(root)
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows[-limit:]


def format_for_prompt(entries: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    for entry in entries:
        lines.append(f"- pattern: {entry.get('pattern', '')}")
        lines.append(f"  mistake: {entry.get('mistake', '')}")
        lines.append(f"  fix: {entry.get('fix', '')}")
    return "\n".join(lines)


def parse_context(args: argparse.Namespace) -> dict[str, Any]:
    if args.context_json:
        return json.loads(args.context_json)
    if not sys.stdin.isatty():
        raw = sys.stdin.read().strip()
        if raw:
            return json.loads(raw)
    return {}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pattern", required=True)
    parser.add_argument("--mistake", required=True)
    parser.add_argument("--fix", required=True)
    parser.add_argument("--actor", default="system")
    parser.add_argument("--context-json", default="")
    args = parser.parse_args()

    try:
        context = parse_context(args)
    except json.JSONDecodeError as exc:
        print(f"invalid context json: {exc}", file=sys.stderr)
        return 2

    path = append_learning(
        pattern=args.pattern,
        mistake=args.mistake,
        fix=args.fix,
        actor=args.actor,
        context=context,
    )
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
