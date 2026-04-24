#!/usr/bin/env python3
"""Operational metrics from append-only harness events."""

from __future__ import annotations

import argparse
import json
from collections import Counter

from common import ROOT


EVENTS = ROOT / "harness" / "telemetry" / "events.jsonl"
LEARNINGS = ROOT / "harness" / "telemetry" / "learnings.jsonl"


def load_jsonl(path):
    if not path.exists():
        return []
    items = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            items.append(json.loads(line))
        except json.JSONDecodeError:
            items.append({"kind": "invalid", "status": "invalid"})
    return items


def metrics() -> dict:
    events = load_jsonl(EVENTS)
    learnings = load_jsonl(LEARNINGS)
    by_kind = Counter(event.get("kind", "unknown") for event in events)
    by_status = Counter(event.get("status", "unknown") for event in events)
    blocked = [event for event in events if event.get("status") in {"blocked", "error", "warning"}]
    return {
        "events_total": len(events),
        "learnings_total": len(learnings),
        "events_by_kind": dict(sorted(by_kind.items())),
        "events_by_status": dict(sorted(by_status.items())),
        "blocked_events": len(blocked),
        "review_accepts": by_status.get("accepted", 0),
        "quality_blocks": len([event for event in events if event.get("kind") == "quality.gate" and event.get("status") == "blocked"]),
        "automation_events": sum(count for kind, count in by_kind.items() if kind.startswith("automation.")),
        "subagent_events": sum(count for kind, count in by_kind.items() if kind.startswith("subagent.")),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    data = metrics()
    if args.json:
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        for key, value in data.items():
            print(f"{key}: {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

