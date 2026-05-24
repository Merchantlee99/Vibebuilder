#!/usr/bin/env python3
"""Validate spec/code drift review ledgers."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from common import ROOT, nonempty_section
from event_log import record_event


DEFAULT_REVIEW = "docs/ai/current/Spec-Review.md"
TEMPLATE = "templates/Spec-Review.md"
VALID_GAPS = {"missing_implementation", "partial_implementation", "missing_test", "wrong_code", "wrong_spec", "decision_gap"}
BLOCKING_IMPACTS = {"blocker", "release_blocker"}
RESOLVED = {"resolved", "accepted", "not_applicable"}


def parse_rows(text: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line.startswith("|") or "SPEC-GAP" not in line:
            continue
        parts = [part.strip() for part in line.strip("|").split("|")]
        if len(parts) < 6:
            continue
        rows.append({
            "id": parts[0],
            "req": parts[1],
            "gap": parts[2],
            "impact": parts[3],
            "status": parts[4],
            "evidence": parts[5],
        })
    return rows


def validate_review(text: str, required: bool) -> tuple[bool, list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    for heading in ["Scope Reviewed", "Drift Findings", "Residual Risk"]:
        if not nonempty_section(text, heading):
            errors.append(f"missing non-empty section: {heading}")
    rows = parse_rows(text)
    if required and not rows:
        errors.append("required spec drift review needs at least one SPEC-GAP row or an explicit not_applicable row")
    for row in rows:
        if row["gap"] not in VALID_GAPS:
            errors.append(f"{row['id']}: invalid gap type {row['gap']}")
        status = row["status"].lower()
        impact = row["impact"].lower()
        if impact in BLOCKING_IMPACTS and status not in RESOLVED:
            errors.append(f"{row['id']}: unresolved blocker drift finding")
        if not row["evidence"]:
            warnings.append(f"{row['id']}: missing evidence note")
    return not errors, errors, warnings


def run_gate(args: argparse.Namespace) -> tuple[bool, list[str], list[str]]:
    path = ROOT / (TEMPLATE if args.template else args.review)
    if not path.exists():
        if args.required:
            return False, [f"missing spec drift review: {path.relative_to(ROOT)}"], []
        return True, [], ["spec drift review not found and not required"]
    text = path.read_text(encoding="utf-8")
    return validate_review(text, args.required or args.template)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review", default=DEFAULT_REVIEW)
    parser.add_argument("--required", action="store_true")
    parser.add_argument("--template", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--warn-only", action="store_true")
    args = parser.parse_args()

    ok, errors, warnings = run_gate(args)
    status = "ok" if ok else ("warning" if args.warn_only else "blocked")
    record_event("spec_drift.gate", actor="harness", status=status, errors=errors, warnings=warnings)
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
