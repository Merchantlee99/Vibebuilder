#!/usr/bin/env python3
"""Block unsafe automatic promotion of inferred team rules."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from common import ROOT, nonempty_section
from event_log import record_event
from team_rule_mining_gate import proposal_paths


DEFAULT_DIR = "harness/team/rule-proposals"
TEMPLATE = "templates/Team-Rule-Proposal.md"
FORBIDDEN_AUTO_TARGETS = {"AGENTS.md", ".codex/config.toml", ".codex/hooks.json", "harness/strict_policy.json"}


def field(text: str, key: str) -> str:
    match = re.search(rf"^{re.escape(key)}:\s*(.*)$", text, re.MULTILINE)
    return match.group(1).strip().strip("`") if match else ""


def validate_promotion(path: Path, allow_agents: bool) -> tuple[list[str], list[str]]:
    text = path.read_text(encoding="utf-8")
    errors: list[str] = []
    warnings: list[str] = []
    status = field(text, "Promotion Status").lower()
    target = field(text, "Promotion Target")
    verdict_match = re.search(r"^## Reviewer Verdict\s*$([\s\S]*?)(?=^## |\Z)", text, re.MULTILINE)
    verdict = verdict_match.group(1).strip().lower() if verdict_match else ""

    if status in {"approved", "active", "promoted"}:
        if "approve" not in verdict:
            errors.append(f"{path.relative_to(ROOT)}: approved/active promotion requires reviewer verdict approve")
        if not nonempty_section(text, "Test Fixture"):
            errors.append(f"{path.relative_to(ROOT)}: approved/active promotion requires Test Fixture")
    if target in FORBIDDEN_AUTO_TARGETS and not allow_agents:
        errors.append(f"{path.relative_to(ROOT)}: promotion target {target} requires explicit --allow-agents")
    if status == "active" and "Collision Check" not in text:
        errors.append(f"{path.relative_to(ROOT)}: active promotion requires collision check")
    if status == "proposed":
        warnings.append(f"{path.relative_to(ROOT)}: proposal is not promoted")
    return errors, warnings


def run_gate(args: argparse.Namespace) -> tuple[bool, list[str], list[str]]:
    paths = [ROOT / TEMPLATE] if args.template else proposal_paths(ROOT / args.path)
    if not paths:
        if args.required:
            return False, [f"no team rule proposals found under {args.path}"], []
        return True, [], ["no team rule proposals found"]
    errors: list[str] = []
    warnings: list[str] = []
    for path in paths:
        proposal_errors, proposal_warnings = validate_promotion(path, args.allow_agents)
        errors.extend(proposal_errors)
        warnings.extend(proposal_warnings)
    return not errors, errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--path", default=DEFAULT_DIR)
    parser.add_argument("--allow-agents", action="store_true")
    parser.add_argument("--required", action="store_true")
    parser.add_argument("--template", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--warn-only", action="store_true")
    args = parser.parse_args()

    ok, errors, warnings = run_gate(args)
    status = "ok" if ok else ("warning" if args.warn_only else "blocked")
    record_event("rule_promotion.gate", actor="harness", status=status, errors=errors, warnings=warnings)
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
