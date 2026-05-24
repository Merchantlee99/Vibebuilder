#!/usr/bin/env python3
"""Validate v6 intent spec artifacts."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from common import ROOT, nonempty_section
from event_log import record_event


DEFAULT_SPEC = "docs/ai/current/Feature-Spec.md"
TEMPLATE = "templates/Feature-Spec.md"
VALID_LAYERS = {"L0", "L1", "L2", "L3"}
REQ_RE = re.compile(r"\bREQ-[A-Z0-9-]+-\d{3}(?::S\d+)?\b")
EARS_RE = re.compile(r"\[(Ubiquitous|Event-driven|State-driven|Unwanted|Optional)\]")


def layer_heading(layer: str) -> str:
    number = layer[1:]
    return f"Layer {number}"


def req_ids(text: str) -> set[str]:
    return set(REQ_RE.findall(text))


def validate_spec(text: str, required_layers: list[str], template: bool = False) -> tuple[bool, list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    if not nonempty_section(text, "Scope"):
        errors.append("missing non-empty section: Scope")

    layers = [layer for layer in required_layers if layer]
    for layer in layers:
        if layer not in VALID_LAYERS:
            errors.append(f"invalid required layer: {layer}")
            continue
        if layer != "L0" and layer_heading(layer) not in text:
            errors.append(f"missing required {layer} section")

    if "L2" in layers or template:
        ids = req_ids(text)
        if not ids:
            errors.append("L2 behavior spec requires at least one REQ statement")
        if not EARS_RE.search(text):
            errors.append("L2 behavior spec requires EARS markers")
        if "[Unwanted]" not in text:
            errors.append("L2 behavior spec requires at least one [Unwanted] statement")

    if "L1" in layers and "Canonical terms" not in text and "Canonical Terms" not in text:
        errors.append("L1 domain truth requires canonical terms")

    if "L3" in layers:
        for phrase in ["Ordering", "Idempotency", "Partial failure"]:
            if phrase not in text:
                errors.append(f"L3 interface contract missing {phrase}")

    if "Generated requirement stub" in text:
        warnings.append("spec references generated stubs; ensure req_evidence_gate maps executed evidence before completion")

    return not errors, errors, warnings


def run_gate(args: argparse.Namespace) -> tuple[bool, list[str], list[str]]:
    path = ROOT / (TEMPLATE if args.template else args.spec)
    if not path.exists():
        return False, [f"missing spec artifact: {path.relative_to(ROOT)}"], []
    layers = args.require_layer or []
    if args.template and not layers:
        layers = ["L1", "L2"]
    text = path.read_text(encoding="utf-8")
    return validate_spec(text, layers, args.template)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", default=DEFAULT_SPEC)
    parser.add_argument("--require-layer", action="append", default=[])
    parser.add_argument("--template", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--warn-only", action="store_true")
    args = parser.parse_args()

    ok, errors, warnings = run_gate(args)
    status = "ok" if ok else ("warning" if args.warn_only else "blocked")
    record_event("spec.gate", actor="harness", status=status, errors=errors, warnings=warnings)
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
