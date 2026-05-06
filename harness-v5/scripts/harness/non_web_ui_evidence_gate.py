#!/usr/bin/env python3
"""Validate evidence for non-browser UI surfaces."""

from __future__ import annotations

import argparse
import json
import sys

from event_log import record_event
from evidence_log import records_for_task


def run_gate(args: argparse.Namespace) -> tuple[bool, list[str], list[str]]:
    if args.template:
        return True, [], []
    errors: list[str] = []
    warnings: list[str] = []
    records, record_errors = records_for_task(args.task_id)
    errors.extend(record_errors)
    ui_records = [record for record in records if record.get("kind") in {"visual", "runtime", "accessibility", "layout", "review"}]
    if args.required and not ui_records:
        errors.append("non-web UI evidence is required but no adapter/manual evidence was found")
    for record in ui_records:
        if record.get("kind") == "visual" and not record.get("artifacts"):
            errors.append(f"{record.get('id', '<visual>')}: non-web visual evidence needs an artifact")
    if not args.adapter and args.required:
        warnings.append("required non-web UI evidence should name an adapter or manual evidence method")
    if not ui_records and not args.required:
        warnings.append("no non-web UI evidence found")
    return not errors, errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task-id", default="")
    parser.add_argument("--adapter", default="")
    parser.add_argument("--required", action="store_true")
    parser.add_argument("--template", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--warn-only", action="store_true")
    args = parser.parse_args()

    ok, errors, warnings = run_gate(args)
    status = "ok" if ok else ("warning" if args.warn_only else "blocked")
    record_event("non_web_ui_evidence.gate", actor="harness", status=status, errors=errors, warnings=warnings)
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
