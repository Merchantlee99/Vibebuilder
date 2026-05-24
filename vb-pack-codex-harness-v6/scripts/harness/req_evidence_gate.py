#!/usr/bin/env python3
"""Validate v6 REQ-to-evidence maps."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from common import ROOT
from event_log import record_event


DEFAULT_MAP = "docs/ai/current/Req-Evidence-Map.md"
DEFAULT_SPEC = "docs/ai/current/Feature-Spec.md"
TEMPLATE = "templates/Req-Evidence-Map.md"
REQ_RE = re.compile(r"\bREQ-[A-Z0-9-]+-\d{3}(?::S\d+)?\b")
VALID_STATES = {"generated_stub", "mapped", "traced", "verified", "manual_only", "blocked", "not_applicable"}
INCOMPLETE_STATES = {"generated_stub", "mapped", "traced"}
COMPLETE_STATES = {"verified", "manual_only", "blocked", "not_applicable"}


def req_ids_from_file(path: Path) -> set[str]:
    if not path.exists():
        return set()
    return set(REQ_RE.findall(path.read_text(encoding="utf-8")))


def parse_map(text: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line.startswith("|") or "REQ-" not in line:
            continue
        parts = [part.strip() for part in line.strip("|").split("|")]
        if len(parts) < 5:
            continue
        rows.append({
            "req": parts[0],
            "state": parts[1],
            "type": parts[2],
            "target": parts[3],
            "record": parts[4],
        })
    return rows


def validate_map(text: str, spec_ids: set[str], allow_planned: bool) -> tuple[bool, list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    rows = parse_map(text)
    if not rows:
        errors.append("REQ Evidence Map needs at least one REQ row")
        return False, errors, warnings

    mapped_ids: set[str] = set()
    for idx, row in enumerate(rows, start=1):
        ids = REQ_RE.findall(row["req"])
        if not ids:
            errors.append(f"row {idx}: missing REQ id")
            continue
        req = ids[0]
        mapped_ids.add(req)
        state = row["state"]
        if state not in VALID_STATES:
            errors.append(f"{req}: invalid evidence state {state}")
        if state in INCOMPLETE_STATES and not allow_planned:
            errors.append(f"{req}: {state} is not completion evidence")
        if state in COMPLETE_STATES and (not row["type"] or not row["target"] or not row["record"]):
            errors.append(f"{req}: complete evidence state requires type, target, and execution / record")

    missing = sorted(spec_ids - mapped_ids)
    for req in missing:
        errors.append(f"{req}: missing from REQ Evidence Map")
    extra = sorted(mapped_ids - spec_ids)
    if spec_ids:
        for req in extra:
            warnings.append(f"{req}: mapped but not found in spec artifact")
    return not errors, errors, warnings


def run_gate(args: argparse.Namespace) -> tuple[bool, list[str], list[str]]:
    map_path = ROOT / (TEMPLATE if args.template else args.map)
    if not map_path.exists():
        return False, [f"missing REQ evidence map: {map_path.relative_to(ROOT)}"], []
    spec_ids = set()
    if args.spec:
        spec_ids = req_ids_from_file(ROOT / args.spec)
    elif not args.template:
        spec_ids = req_ids_from_file(ROOT / DEFAULT_SPEC)
    text = map_path.read_text(encoding="utf-8")
    return validate_map(text, spec_ids, args.allow_planned or args.template)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--map", default=DEFAULT_MAP)
    parser.add_argument("--spec", default="")
    parser.add_argument("--allow-planned", action="store_true")
    parser.add_argument("--template", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--warn-only", action="store_true")
    args = parser.parse_args()

    ok, errors, warnings = run_gate(args)
    status = "ok" if ok else ("warning" if args.warn_only else "blocked")
    record_event("req_evidence.gate", actor="harness", status=status, errors=errors, warnings=warnings)
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
