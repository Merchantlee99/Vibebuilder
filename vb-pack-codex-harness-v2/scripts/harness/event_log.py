#!/usr/bin/env python3
"""Append-only event and learning logs for Codex Harness v2."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from common import ROOT, append_jsonl, event_id, utc_slug


EVENTS_PATH = ROOT / "harness" / "telemetry" / "events.jsonl"
LEARNINGS_PATH = ROOT / "harness" / "telemetry" / "learnings.jsonl"


def record_event(kind: str, actor: str = "harness", status: str = "ok", **data) -> dict:
    event = {
        "id": event_id(kind),
        "ts": utc_slug(),
        "kind": kind,
        "actor": actor,
        "status": status,
        "data": data,
    }
    append_jsonl(EVENTS_PATH, event)
    return event


def record_learning(summary: str, source_event: str = "", severity: str = "info", **data) -> dict:
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
    raise AssertionError(args.command)


if __name__ == "__main__":
    raise SystemExit(main())

