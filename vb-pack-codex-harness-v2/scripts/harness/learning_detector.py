#!/usr/bin/env python3
"""Detect repeated failures and propose learnings without auto-promoting skills."""

from __future__ import annotations

import argparse
import json
from collections import Counter

from common import ROOT
from event_log import record_learning


EVENTS = ROOT / "harness" / "telemetry" / "events.jsonl"


def load_events() -> list[dict]:
    if not EVENTS.exists():
        return []
    events = []
    for line in EVENTS.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return events


def detect(threshold: int) -> list[dict]:
    events = load_events()
    blocked = [event for event in events if event.get("status") in {"blocked", "error", "warning"}]
    keys = []
    for event in blocked:
        data = event.get("data", {})
        reason = data.get("reason") or ",".join(data.get("errors", [])[:2]) or event.get("status")
        keys.append((event.get("kind", "unknown"), reason))
    counts = Counter(keys)
    findings = []
    for (kind, reason), count in counts.items():
        if count >= threshold:
            findings.append({"kind": kind, "reason": reason, "count": count})
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--threshold", type=int, default=2)
    parser.add_argument("--record", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    findings = detect(args.threshold)
    if args.record:
        for finding in findings:
            record_learning(
                f"Repeated harness issue: {finding['kind']} / {finding['reason']}",
                severity="warning",
                repeated_count=finding["count"],
                kind=finding["kind"],
                reason=finding["reason"],
            )
    if args.json:
        print(json.dumps({"findings": findings}, indent=2, ensure_ascii=False))
    else:
        if not findings:
            print("no repeated failures")
        for finding in findings:
            print(f"{finding['kind']} x{finding['count']}: {finding['reason']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

