#!/usr/bin/env python3
"""Validate implementation evidence for normal+ work."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from common import ROOT, nonempty_section, read_text, tier_at_least
from event_log import record_event
from evidence_log import records_for_task


def latest_review_file() -> Path | None:
    files = sorted((ROOT / "harness/reviews").glob("review-*.md"))
    return files[-1] if files else None


def check_template() -> tuple[bool, list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    for rel in ["templates/Implement.md", "templates/Review.md", "templates/Task-Profile.json"]:
        if not (ROOT / rel).exists():
            errors.append(f"missing template: {rel}")
    return not errors, errors, warnings


def run_gate(args: argparse.Namespace) -> tuple[bool, list[str], list[str]]:
    if args.template:
        return check_template()
    errors: list[str] = []
    warnings: list[str] = []

    artifact_dir = ROOT / args.artifact_dir
    implement = artifact_dir / "Implement.md"
    if tier_at_least(args.tier, "normal"):
        text = read_text(implement)
        if not text:
            errors.append(f"missing implementation artifact: {implement.relative_to(ROOT)}")
        elif not nonempty_section(text, "Validation"):
            errors.append("Implement.md requires non-empty Validation")

    if args.task_id and tier_at_least(args.tier, "normal"):
        records, record_errors = records_for_task(args.task_id)
        errors.extend(record_errors)
        command_records = [record for record in records if record.get("kind") == "command"]
        if not command_records:
            errors.append("normal+ work requires at least one command evidence record")
        elif not any(record.get("exit_code") == 0 and record.get("status") == "pass" for record in command_records):
            errors.append("normal+ work requires a passing command evidence record")

        review_records = [record for record in records if record.get("kind") == "review"]
        review_file = ROOT / args.review_file if args.review_file else latest_review_file()
        if not review_records and review_file is None:
            warnings.append("no review evidence record or review file found")

    if not args.task_id and tier_at_least(args.tier, "normal"):
        errors.append("normal+ implementation evidence requires --task-id")

    return not errors, errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tier", choices=["trivial", "normal", "high-risk"], default="normal")
    parser.add_argument("--task-id", default="")
    parser.add_argument("--artifact-dir", default="docs/ai/current")
    parser.add_argument("--review-file", default="")
    parser.add_argument("--template", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--warn-only", action="store_true")
    args = parser.parse_args()

    ok, errors, warnings = run_gate(args)
    status = "ok" if ok else ("warning" if args.warn_only else "blocked")
    record_event("implementation.gate", actor="harness", status=status, tier=args.tier, errors=errors, warnings=warnings)
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
