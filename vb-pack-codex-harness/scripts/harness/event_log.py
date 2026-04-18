#!/usr/bin/env python3
"""Append-only event logging for the Codex-native harness."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from session_state import resolve_session_id as _stable_session_id
else:  # pragma: no cover - package import path
    from .session_state import resolve_session_id as _stable_session_id


LOG_DIR = Path(".codex/telemetry")
LOG_FILE = "events.jsonl"


def repo_root() -> Path:
    current = Path.cwd().resolve()
    for candidate in (current, *current.parents):
        if (candidate / ".codex").exists() or (candidate / ".git").exists():
            return candidate
    return current


def resolve_session_id() -> str:
    return _stable_session_id(repo_root())


def log_path(root: Path | None = None) -> Path:
    base = root or repo_root()
    return base / LOG_DIR / LOG_FILE


def append_event(
    *,
    kind: str,
    actor: str,
    summary: str,
    files: list[str] | None = None,
    stage: str = "",
    detail: dict[str, Any] | None = None,
    root: Path | None = None,
) -> Path:
    path = log_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "kind": kind,
        "actor": actor,
        "summary": summary,
        "files": files or [],
        "stage": stage,
        "session": resolve_session_id(),
        "detail": detail or {},
    }
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    return path


def iter_events(root: Path | None = None):
    path = log_path(root)
    if not path.exists():
        return
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def parse_detail(args: argparse.Namespace) -> dict[str, Any]:
    detail: dict[str, Any] = {}
    if args.detail_json:
        detail = json.loads(args.detail_json)
    elif not sys.stdin.isatty():
        raw = sys.stdin.read().strip()
        if raw:
            detail = json.loads(raw)
    return detail


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("kind")
    parser.add_argument("actor")
    parser.add_argument("summary")
    parser.add_argument("--stage", default="")
    parser.add_argument("--file", dest="files", action="append", default=[])
    parser.add_argument("--detail-json", default="")
    args = parser.parse_args()

    try:
        detail = parse_detail(args)
    except json.JSONDecodeError as exc:
        print(f"invalid detail json: {exc}", file=sys.stderr)
        return 2

    path = append_event(
        kind=args.kind,
        actor=args.actor,
        summary=args.summary,
        files=args.files,
        stage=args.stage,
        detail=detail,
    )
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
