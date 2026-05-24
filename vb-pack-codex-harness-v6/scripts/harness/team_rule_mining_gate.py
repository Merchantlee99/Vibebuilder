#!/usr/bin/env python3
"""Validate inferred team-rule proposals before promotion."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from common import ROOT, nonempty_section
from event_log import record_event


DEFAULT_DIR = "harness/team/rule-proposals"
TEMPLATE = "templates/Team-Rule-Proposal.md"
HIGH_RISK_TERMS = {"auth", "payment", "billing", "deletion", "privacy", "migration", "security", "public api", "agents.md", "design system"}


def section_body(text: str, heading: str) -> str:
    match = re.search(rf"^## {re.escape(heading)}\s*$([\s\S]*?)(?=^## |\Z)", text, re.MULTILINE | re.IGNORECASE)
    return match.group(1).strip() if match else ""


def proposal_paths(root: Path) -> list[Path]:
    if root.is_file():
        return [root]
    if not root.exists():
        return []
    return sorted(path for path in root.glob("*.md") if path.name != "README.md")


def validate_proposal(path: Path, min_evidence: int) -> tuple[list[str], list[str]]:
    text = path.read_text(encoding="utf-8")
    errors: list[str] = []
    warnings: list[str] = []
    for heading in ["Observed Pattern", "Evidence", "Proposed Rule", "Scope", "Collision Check", "Test Fixture", "Reviewer Verdict"]:
        if not nonempty_section(text, heading):
            errors.append(f"{path.relative_to(ROOT)}: missing non-empty section: {heading}")

    if "Promotion Status: proposed" not in text and "Promotion Status: approved" not in text and "Promotion Status: active" not in text:
        errors.append(f"{path.relative_to(ROOT)}: missing Promotion Status")
    evidence_lines = [line for line in section_body(text, "Evidence").splitlines() if line.strip().startswith("-")]
    if len(evidence_lines) < min_evidence:
        errors.append(f"{path.relative_to(ROOT)}: needs at least {min_evidence} evidence bullets")

    lowered = text.lower()
    if any(term in lowered for term in HIGH_RISK_TERMS) and "Reviewer Verdict\n\napprove" not in text:
        warnings.append(f"{path.relative_to(ROOT)}: high-risk/global rule terms need explicit reviewer approval before promotion")
    if "Promotion Target: `AGENTS.md`" in text or "Promotion Target: AGENTS.md" in text:
        warnings.append(f"{path.relative_to(ROOT)}: AGENTS.md always-rule promotion requires separate human review")
    return errors, warnings


def run_gate(args: argparse.Namespace) -> tuple[bool, list[str], list[str]]:
    if args.template:
        paths = [ROOT / TEMPLATE]
    else:
        paths = proposal_paths(ROOT / args.path)
    if not paths:
        if args.required:
            return False, [f"no team rule proposals found under {args.path}"], []
        return True, [], ["no team rule proposals found"]

    errors: list[str] = []
    warnings: list[str] = []
    for path in paths:
        proposal_errors, proposal_warnings = validate_proposal(path, args.min_evidence)
        errors.extend(proposal_errors)
        warnings.extend(proposal_warnings)
    return not errors, errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--path", default=DEFAULT_DIR)
    parser.add_argument("--min-evidence", type=int, default=2)
    parser.add_argument("--required", action="store_true")
    parser.add_argument("--template", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--warn-only", action="store_true")
    args = parser.parse_args()

    ok, errors, warnings = run_gate(args)
    status = "ok" if ok else ("warning" if args.warn_only else "blocked")
    record_event("team_rule_mining.gate", actor="harness", status=status, errors=errors, warnings=warnings)
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
