#!/usr/bin/env python3
"""Stable Codex session identity persisted to the repository control plane."""

from __future__ import annotations

import argparse
import json
import os
import time
import uuid
from pathlib import Path


SESSION_ENV = "CODEX_SESSION_ID"
SESSION_FILE = Path(".codex/context/session.json")


def repo_root() -> Path:
    current = Path.cwd().resolve()
    for candidate in (current, *current.parents):
        if (candidate / ".codex").exists() or (candidate / ".git").exists():
            return candidate
    return current


def session_path(root: Path | None = None) -> Path:
    return (root or repo_root()) / SESSION_FILE


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _new_payload(source: str) -> dict[str, str]:
    return {
        "session_id": f"session-{uuid.uuid4().hex[:12]}",
        "created_at": _now(),
        "updated_at": _now(),
        "source": source,
    }


def load_state(root: Path | None = None) -> dict[str, str] | None:
    path = session_path(root)
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict) or not payload.get("session_id"):
        return None
    return payload


def save_state(payload: dict[str, str], root: Path | None = None) -> Path:
    path = session_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = dict(payload)
    payload["updated_at"] = _now()
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def resolve_session_id(root: Path | None = None) -> str:
    env_sid = os.environ.get(SESSION_ENV, "").strip()
    if env_sid:
        payload = _new_payload("env")
        payload["session_id"] = env_sid
        save_state(payload, root)
        return env_sid

    payload = load_state(root)
    if payload:
        save_state(payload, root)
        return payload["session_id"]

    payload = _new_payload("generated")
    save_state(payload, root)
    return payload["session_id"]


def refresh_session(root: Path | None = None) -> str:
    payload = _new_payload("refreshed")
    save_state(payload, root)
    return payload["session_id"]


def clear_session(root: Path | None = None) -> None:
    path = session_path(root)
    if path.exists():
        path.unlink()


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=False)
    sub.add_parser("show")
    sub.add_parser("refresh")
    sub.add_parser("clear")
    args = parser.parse_args()

    if args.cmd in (None, "show"):
        print(resolve_session_id())
        return 0
    if args.cmd == "refresh":
        print(refresh_session())
        return 0
    clear_session()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
