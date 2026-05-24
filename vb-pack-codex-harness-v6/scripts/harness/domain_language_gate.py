#!/usr/bin/env python3
"""Validate v6 domain language artifacts."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from common import ROOT, nonempty_section
from event_log import record_event


DEFAULT_PATH = "docs/ai/current/Domain-Language.md"
TEMPLATE = "templates/Domain-Language.md"


def section_body(text: str, heading: str) -> str:
    match = re.search(rf"^## {re.escape(heading)}\s*$([\s\S]*?)(?=^## |\Z)", text, re.MULTILINE)
    return match.group(1).strip() if match else ""


def validate_text(text: str, terms: list[str], required: bool) -> tuple[bool, list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    required_sections = ["Scope", "Canonical Terms", "Entities", "States", "Invariants", "Open Questions"]
    for heading in required_sections:
        if not nonempty_section(text, heading):
            errors.append(f"missing non-empty section: {heading}")

    canonical = section_body(text, "Canonical Terms")
    for term in terms:
        if term and term not in canonical and term not in text:
            errors.append(f"required term not documented: {term}")

    if "Rejected aliases" not in canonical and required:
        warnings.append("Canonical Terms should document rejected aliases or state none")
    if "TBD" in text or "TODO" in text:
        warnings.append("domain language contains TODO/TBD")
    return not errors, errors, warnings


def run_gate(args: argparse.Namespace) -> tuple[bool, list[str], list[str]]:
    path = ROOT / (TEMPLATE if args.template else args.path)
    if not path.exists():
        if args.required or args.template:
            return False, [f"missing domain language artifact: {path.relative_to(ROOT)}"], []
        return True, [], ["domain language artifact not found and not required"]
    text = path.read_text(encoding="utf-8")
    return validate_text(text, args.term, args.required or args.template)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--path", default=DEFAULT_PATH)
    parser.add_argument("--term", action="append", default=[])
    parser.add_argument("--required", action="store_true")
    parser.add_argument("--template", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--warn-only", action="store_true")
    args = parser.parse_args()

    ok, errors, warnings = run_gate(args)
    status = "ok" if ok else ("warning" if args.warn_only else "blocked")
    record_event("domain_language.gate", actor="harness", status=status, errors=errors, warnings=warnings)
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
