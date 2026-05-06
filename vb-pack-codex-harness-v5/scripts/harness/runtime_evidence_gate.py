#!/usr/bin/env python3
"""Validate runtime/debug evidence for reproduced behavior."""

from __future__ import annotations

import argparse
import json
import sys

from event_log import record_event
from evidence_log import records_for_task


def run_gate(args: argparse.Namespace) -> tuple[bool, list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    if args.template:
        return True, errors, warnings

    records, record_errors = records_for_task(args.task_id)
    errors.extend(record_errors)
    runtime = [record for record in records if record.get("kind") == "runtime"]
    if args.required and not runtime:
        errors.append("runtime evidence is required but no runtime record was found")
    for record in runtime:
        label = record.get("id", "<runtime>")
        if not record.get("summary"):
            errors.append(f"{label}: runtime evidence missing summary")
        if not record.get("route") and not record.get("command"):
            warnings.append(f"{label}: runtime evidence should include route or command")
        if record.get("status") == "fail":
            errors.append(f"{label}: runtime evidence status is fail")
    if not runtime and not args.required:
        warnings.append("no runtime evidence found")
    return not errors, errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task-id", default="")
    parser.add_argument("--required", action="store_true")
    parser.add_argument("--template", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--warn-only", action="store_true")
    args = parser.parse_args()

    ok, errors, warnings = run_gate(args)
    status = "ok" if ok else ("warning" if args.warn_only else "blocked")
    record_event("runtime_evidence.gate", actor="harness", status=status, errors=errors, warnings=warnings)
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
