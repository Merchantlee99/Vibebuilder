#!/usr/bin/env python3
"""Audit Hermes-style memory and self-improvement proposals."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from common import ROOT
from event_log import record_event


PROPOSED_MEMORY = ROOT / "harness" / "memory" / "proposed-learnings.jsonl"
REQUIRED_FIELDS = [
    "source_id",
    "occurrence_count",
    "confidence",
    "review_date",
    "proposed_action",
    "reviewer_verdict",
]


def load_jsonl(path: Path) -> tuple[list[dict], list[str]]:
    records: list[dict] = []
    errors: list[str] = []
    if not path.exists():
        return records, errors
    for line_no, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not raw_line.strip():
            continue
        try:
            records.append(json.loads(raw_line))
        except json.JSONDecodeError as exc:
            errors.append(f"{path.relative_to(ROOT)}:{line_no}: invalid json: {exc}")
    return records, errors


def validate_record(record: dict, label: str) -> list[str]:
    errors: list[str] = []
    for field in REQUIRED_FIELDS:
        if record.get(field) in {"", None}:
            errors.append(f"{label}: missing {field}")
    if int(record.get("occurrence_count", 0) or 0) < 2:
        errors.append(f"{label}: occurrence_count must be >= 2")
    confidence = record.get("confidence")
    if not isinstance(confidence, (int, float)) or confidence < 0 or confidence > 1:
        errors.append(f"{label}: confidence must be a number from 0 to 1")
    verdict = str(record.get("reviewer_verdict", "")).lower()
    if verdict not in {"quarantine", "reject", "promote-with-review", "promote"}:
        errors.append(f"{label}: reviewer_verdict must be quarantine, reject, promote-with-review, or promote")
    if verdict == "promote" and not record.get("explicit_approval"):
        errors.append(f"{label}: promote requires explicit_approval")
    if not record.get("test_fixture"):
        errors.append(f"{label}: missing test_fixture")
    return errors


def audit(path: Path) -> tuple[bool, list[str], list[str]]:
    records, errors = load_jsonl(path)
    warnings: list[str] = []
    for idx, record in enumerate(records, start=1):
        errors.extend(validate_record(record, f"line {idx}"))
    if not records:
        warnings.append("no memory proposals found")
    return not errors, errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    audit_cmd = sub.add_parser("audit")
    audit_cmd.add_argument("--path", default=str(PROPOSED_MEMORY.relative_to(ROOT)))
    audit_cmd.add_argument("--json", action="store_true")
    audit_cmd.add_argument("--warn-only", action="store_true")
    args = parser.parse_args()

    path = ROOT / args.path
    ok, errors, warnings = audit(path)
    status = "ok" if ok else ("warning" if args.warn_only else "blocked")
    record_event("memory.guard", actor="harness", status=status, errors=errors, warnings=warnings)
    payload_ok = ok or args.warn_only
    if args.json:
        print(json.dumps({"ok": payload_ok, "errors": errors, "warnings": warnings}, indent=2, ensure_ascii=False))
    else:
        for warning in warnings:
            print(f"WARN: {warning}")
        for error in errors:
            print(f"{'WARN' if args.warn_only else 'ERROR'}: {error}", file=sys.stderr)
        print("PASS" if payload_ok else "FAIL")
    return 0 if payload_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
