#!/usr/bin/env python3
"""Detect repeated failures and propose learnings without auto-promoting skills."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter

from event_log import iter_events, record_learning


def load_events() -> list[dict]:
    return iter_events()


def detect(threshold: int) -> list[dict]:
    events = load_events()
    blocked = [event for event in events if event.get("status") in {"blocked", "error", "warning"}]
    keys = []
    for event in blocked:
        data = event.get("data", {})
        reason = canonical_reason(data.get("reason"), data.get("errors", []), event.get("status"))
        keys.append((event.get("kind", "unknown"), reason))
    counts = Counter(keys)
    findings = []
    for (kind, reason), count in counts.items():
        if count >= threshold:
            findings.append({"kind": kind, "reason": reason, "count": count})
    return findings


def canonical_reason(reason, errors, fallback) -> str:
    if reason:
        return normalize_text(str(reason))
    if isinstance(errors, list) and errors:
        normalized = sorted(normalize_text(str(error)) for error in errors if str(error).strip())
        return "|".join(normalized[:3]) or normalize_text(str(fallback))
    return normalize_text(str(fallback))


def normalize_text(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(r"\b[0-9a-f]{8,}\b", "<hex>", value)
    value = re.sub(r"\d{4,}", "<num>", value)
    value = re.sub(r"\s+", " ", value)
    return value


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
