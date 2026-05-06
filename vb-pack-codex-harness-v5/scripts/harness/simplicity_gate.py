#!/usr/bin/env python3
"""Check Karpathy-style simplicity and surgical-change evidence."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from common import ROOT, nonempty_section, read_text
from event_log import record_event


TEMPLATE = ROOT / "templates" / "Simplicity-Review.md"
COMPLEXITY_TERMS = [
    "future-proof",
    "generic framework",
    "extensible",
    "plugin architecture",
    "abstract factory",
    "for later",
    "just in case",
    "추후 확장",
    "범용 프레임워크",
]


def section_text(text: str, heading: str) -> str:
    match = re.search(rf"^## {re.escape(heading)}\s*$([\s\S]*?)(?=^## |\Z)", text, re.MULTILINE)
    return match.group(1).strip() if match else ""


def artifact_path(args: argparse.Namespace) -> Path:
    if args.template:
        return TEMPLATE
    if args.file:
        return ROOT / args.file
    return ROOT / args.artifact_dir / "Simplicity-Review.md"


def run_gate(args: argparse.Namespace) -> tuple[bool, list[str], list[str]]:
    path = artifact_path(args)
    warnings: list[str] = []
    errors: list[str] = []

    if not path.exists():
        if args.required:
            errors.append(f"missing simplicity artifact: {path.relative_to(ROOT)}")
        else:
            warnings.append(f"missing optional simplicity artifact: {path.relative_to(ROOT)}")
        return not errors, errors, warnings

    text = read_text(path)
    for heading in [
        "Assumptions",
        "Simplest Viable Path",
        "Rejected Complexity",
        "Surgical Change Evidence",
        "Validation Criteria",
        "Residual Uncertainty",
    ]:
        if not nonempty_section(text, heading):
            errors.append(f"missing non-empty section: {heading}")

    lowered = text.lower()
    found_terms = [term for term in COMPLEXITY_TERMS if term.lower() in lowered]
    if found_terms and "Rejected Complexity" not in text:
        errors.append(f"complexity terms found without rejection evidence: {found_terms}")
    if found_terms:
        warnings.append(f"complexity terms require explicit justification or rejection: {found_terms}")

    validation = section_text(text, "Validation Criteria")
    if validation and not re.search(r"\b(test|check|verify|pass|fail|command|검증|테스트|명령)\b", validation, re.I):
        errors.append("validation criteria lacks deterministic check language")

    return not errors, errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-dir", default="docs/ai/current")
    parser.add_argument("--file")
    parser.add_argument("--template", action="store_true")
    parser.add_argument("--required", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--warn-only", action="store_true")
    args = parser.parse_args()

    ok, errors, warnings = run_gate(args)
    status = "ok" if ok else ("warning" if args.warn_only else "blocked")
    record_event("simplicity.gate", actor="harness", status=status, errors=errors, warnings=warnings)

    payload = {"ok": ok or args.warn_only, "errors": errors, "warnings": warnings}
    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        for warning in warnings:
            print(f"WARN: {warning}", file=sys.stderr)
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        print("PASS" if payload["ok"] else "FAIL")
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
