#!/usr/bin/env python3
"""Validate v5 UI evidence without judging visual taste."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from common import ROOT
from event_log import record_event
from evidence_log import records_for_task
from task_profile_gate import load_profile, validate_profile


NON_SCREENSHOT_KINDS = {"accessibility", "layout", "runtime", "review", "static-frontend"}


def profile_ui_state(profile_path: str) -> tuple[str, str, str, list[str], list[str]]:
    if not profile_path:
        return "optional", "", "", [], []
    profile, load_errors = load_profile(ROOT / profile_path)
    if load_errors:
        return "optional", "", "", load_errors, []
    _, errors, warnings = validate_profile(profile)
    return (
        profile.get("ui_evidence", "optional"),
        profile.get("not_applicable_reason", ""),
        profile.get("residual_risk", ""),
        errors,
        warnings,
    )


def check_template() -> tuple[bool, list[str], list[str]]:
    errors: list[str] = []
    for rel in ["templates/Visual-Evidence.md", "templates/UI-Review.md", "templates/UI-UX-Brief.md"]:
        if not (ROOT / rel).exists():
            errors.append(f"missing template: {rel}")
    return not errors, errors, []


def run_gate(args: argparse.Namespace) -> tuple[bool, list[str], list[str]]:
    if args.template:
        return check_template()
    errors: list[str] = []
    warnings: list[str] = []

    ui_state, not_applicable_reason, residual_risk, profile_errors, profile_warnings = profile_ui_state(args.profile)
    errors.extend(profile_errors)
    warnings.extend(profile_warnings)
    if args.required:
        ui_state = "required"

    if ui_state == "not-applicable":
        if not not_applicable_reason or not residual_risk:
            errors.append("not-applicable UI evidence requires not_applicable_reason and residual_risk")
        return not errors, errors, warnings

    records, record_errors = records_for_task(args.task_id)
    errors.extend(record_errors)
    visual = [record for record in records if record.get("kind") == "visual"]
    non_screenshot = [record for record in records if record.get("kind") in NON_SCREENSHOT_KINDS]

    if ui_state == "required":
        if not args.task_id:
            errors.append("required UI evidence needs --task-id")
        if not visual:
            errors.append("required UI evidence needs at least one visual evidence record")
        if args.tier in {"normal", "high-risk"} and not non_screenshot:
            errors.append("normal+ UI evidence cannot be screenshot-only; add layout, accessibility, runtime, static-frontend, or review evidence")

    for record in visual:
        label = record.get("id", "<visual>")
        for field in ["route", "viewport", "state"]:
            if not record.get(field):
                errors.append(f"{label}: visual evidence missing {field}")
        artifacts = record.get("artifacts", [])
        no_screenshot_reason = record.get("no_screenshot_reason", "")
        if not artifacts and not no_screenshot_reason:
            errors.append(f"{label}: visual evidence needs a screenshot/platform artifact or no_screenshot_reason")
        if args.sensitive and not record.get("redacted") and not record.get("not_applicable_reason"):
            if not no_screenshot_reason:
                errors.append(f"{label}: sensitive UI must be redacted or carry no_screenshot_reason")

    if ui_state == "optional" and not visual:
        warnings.append("UI evidence optional and no visual evidence found")

    return not errors, errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task-id", default="")
    parser.add_argument("--tier", choices=["trivial", "normal", "high-risk"], default="normal")
    parser.add_argument("--profile", default="")
    parser.add_argument("--required", action="store_true")
    parser.add_argument("--sensitive", action="store_true")
    parser.add_argument("--template", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--warn-only", action="store_true")
    args = parser.parse_args()

    ok, errors, warnings = run_gate(args)
    status = "ok" if ok else ("warning" if args.warn_only else "blocked")
    record_event("ui_evidence.gate", actor="harness", status=status, tier=args.tier, errors=errors, warnings=warnings)
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
