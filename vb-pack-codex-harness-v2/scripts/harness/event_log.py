#!/usr/bin/env python3
"""Append-only event and learning logs for Codex Harness v2."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path

from common import ROOT, append_jsonl, event_id, utc_slug


EVENTS_PATH = ROOT / "harness" / "telemetry" / "events.jsonl"
LEARNINGS_PATH = ROOT / "harness" / "telemetry" / "learnings.jsonl"
LOCK_PATH = ROOT / "harness" / "telemetry" / "events.lock"


@contextmanager
def event_lock():
    LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOCK_PATH.open("a+", encoding="utf-8") as lock:
        try:
            import fcntl
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
            yield
            fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
        except ImportError:
            yield


def record_event(kind: str, actor: str = "harness", status: str = "ok", **data) -> dict:
    with event_lock():
        prev_hash = latest_hash(EVENTS_PATH)
        event = {
            "id": event_id(kind),
            "ts": utc_slug(),
            "kind": kind,
            "actor": actor,
            "status": status,
            "data": data,
            "prev_hash": prev_hash,
        }
        event["hash"] = event_hash(event)
        append_jsonl(EVENTS_PATH, event)
        return event


def record_learning(summary: str, source_event: str = "", severity: str = "info", **data) -> dict:
    with event_lock():
        learning = {
            "id": event_id("learning"),
            "ts": utc_slug(),
            "summary": summary,
            "source_event": source_event,
            "severity": severity,
            "data": data,
        }
        append_jsonl(LEARNINGS_PATH, learning)
        return learning


def tail(path: Path, limit: int) -> list[dict]:
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()[-limit:]
    items = []
    for line in lines:
        try:
            items.append(json.loads(line))
        except json.JSONDecodeError:
            items.append({"invalid": line})
    return items


def canonical_event(event: dict) -> str:
    body = {key: value for key, value in event.items() if key != "hash"}
    return json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def event_hash(event: dict) -> str:
    return hashlib.sha256(canonical_event(event).encode("utf-8")).hexdigest()


def latest_hash(path: Path) -> str:
    if not path.exists():
        return ""
    for line in reversed(path.read_text(encoding="utf-8").splitlines()):
        if not line.strip():
            continue
        try:
            return json.loads(line).get("hash", "")
        except json.JSONDecodeError:
            return ""
    return ""


def verify_events() -> tuple[bool, list[str]]:
    errors = []
    prev = ""
    if not EVENTS_PATH.exists():
        return True, errors
    for idx, line in enumerate(EVENTS_PATH.read_text(encoding="utf-8").splitlines(), start=1):
        try:
            event = json.loads(line)
        except json.JSONDecodeError as exc:
            errors.append(f"line {idx}: invalid json: {exc}")
            continue
        if event.get("prev_hash", "") != prev:
            errors.append(f"line {idx}: prev_hash mismatch")
        expected = event_hash(event)
        if event.get("hash") != expected:
            errors.append(f"line {idx}: hash mismatch")
        prev = event.get("hash", "")
    return not errors, errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    event = sub.add_parser("event")
    event.add_argument("--kind", required=True)
    event.add_argument("--actor", default="harness")
    event.add_argument("--status", default="ok")
    event.add_argument("--data-json", default="{}")

    learning = sub.add_parser("learning")
    learning.add_argument("--summary", required=True)
    learning.add_argument("--source-event", default="")
    learning.add_argument("--severity", choices=["info", "warning", "error"], default="info")
    learning.add_argument("--data-json", default="{}")

    show = sub.add_parser("tail")
    show.add_argument("--log", choices=["events", "learnings"], default="events")
    show.add_argument("--limit", type=int, default=20)

    sub.add_parser("verify")

    args = parser.parse_args()
    if args.command == "event":
        data = json.loads(args.data_json)
        print(json.dumps(record_event(args.kind, args.actor, args.status, **data), indent=2))
        return 0
    if args.command == "learning":
        data = json.loads(args.data_json)
        print(json.dumps(record_learning(args.summary, args.source_event, args.severity, **data), indent=2))
        return 0
    if args.command == "tail":
        path = EVENTS_PATH if args.log == "events" else LEARNINGS_PATH
        print(json.dumps(tail(path, args.limit), indent=2))
        return 0
    if args.command == "verify":
        ok, errors = verify_events()
        if errors:
            for error in errors:
                print(f"ERROR: {error}")
        print("event log ok" if ok else "event log corrupted")
        return 0 if ok else 1
    raise AssertionError(args.command)


if __name__ == "__main__":
    raise SystemExit(main())
