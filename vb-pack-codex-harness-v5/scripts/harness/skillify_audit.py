#!/usr/bin/env python3
"""Audit Codex skills and proposed skills for routing quality."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from common import ROOT, parse_frontmatter, read_text


SKILLS_ROOT = ROOT / ".agents" / "skills"
PROPOSED_ROOT = ROOT / "harness" / "proposed-skills"


def skill_files() -> list[Path]:
    return sorted(SKILLS_ROOT.glob("*/SKILL.md"))


def proposed_files() -> list[Path]:
    return sorted(path for path in PROPOSED_ROOT.glob("*.md") if path.name.lower() != "readme.md")


def words(value: str) -> set[str]:
    return {part for part in re.split(r"[^a-z0-9_-]+", value.lower()) if len(part) >= 4}


def audit_skills(strict: bool = False) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    seen_names: dict[str, Path] = {}
    descriptions: dict[str, str] = {}

    files = skill_files()
    if not files:
        errors.append("no skills found under .agents/skills")

    for path in files:
        text = read_text(path)
        meta = parse_frontmatter(text)
        name = meta.get("name", "")
        description = meta.get("description", "")
        rel = path.relative_to(ROOT)
        if not name:
            errors.append(f"{rel}: missing frontmatter name")
        if not description:
            errors.append(f"{rel}: missing frontmatter description")
        if name in seen_names:
            errors.append(f"{rel}: duplicate skill name also used by {seen_names[name].relative_to(ROOT)}")
        seen_names[name] = path
        descriptions[name] = description
        if len(description) < 40:
            warnings.append(f"{rel}: description may be too short for reliable routing")
        if "use when" not in description.lower():
            warnings.append(f"{rel}: description should include a clear 'Use when' trigger")
        if "do not" not in text.lower() and "non-trigger" not in text.lower():
            warnings.append(f"{rel}: skill lacks explicit non-trigger or boundary guidance")

    names = list(descriptions)
    for idx, left in enumerate(names):
        for right in names[idx + 1:]:
            overlap = words(descriptions[left]) & words(descriptions[right])
            if len(overlap) >= 8:
                warnings.append(f"possible routing overlap: {left} <-> {right} ({', '.join(sorted(overlap)[:8])})")

    if strict:
        errors.extend(warnings)
        warnings = []
    return errors, warnings


def audit_routing_eval(strict: bool = False) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    known_skills = {parse_frontmatter(read_text(path)).get("name", "") for path in skill_files()}
    eval_files = sorted(SKILLS_ROOT.glob("*/routing-eval.jsonl"))
    for path in eval_files:
        rel = path.relative_to(ROOT)
        for line_no, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            line = raw_line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError as exc:
                errors.append(f"{rel}:{line_no}: invalid jsonl: {exc}")
                continue
            intent = item.get("intent", "")
            expected = item.get("expected_skill", "")
            if not intent or not expected:
                errors.append(f"{rel}:{line_no}: requires intent and expected_skill")
                continue
            if expected not in known_skills:
                errors.append(f"{rel}:{line_no}: expected_skill is not installed: {expected}")
            if expected.replace("-", " ") in intent.lower() or expected in intent.lower():
                warnings.append(f"{rel}:{line_no}: intent may be tautological for {expected}")
    if strict:
        errors.extend(warnings)
        warnings = []
    return errors, warnings


def audit_proposed(strict: bool = False) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    required_headings = [
        "Name",
        "Problem",
        "Trigger",
        "Non-Trigger",
        "Instructions",
        "Output Contract",
        "Routing Risks",
        "Validation",
    ]

    for path in proposed_files():
        text = read_text(path)
        rel = path.relative_to(ROOT)
        for heading in required_headings:
            if not re.search(rf"^## {re.escape(heading)}\s*$", text, re.MULTILINE):
                errors.append(f"{rel}: missing heading {heading}")
        if "SKILLIFY_STUB" in text:
            errors.append(f"{rel}: contains SKILLIFY_STUB")
        if "Trigger" in text and "Non-Trigger" not in text:
            warnings.append(f"{rel}: trigger exists without non-trigger boundary")

    if strict:
        errors.extend(warnings)
        warnings = []
    return errors, warnings


def report(errors: list[str], warnings: list[str], as_json: bool) -> int:
    if as_json:
        print(json.dumps({"ok": not errors, "errors": errors, "warnings": warnings}, indent=2))
    else:
        for warning in warnings:
            print(f"WARN: {warning}")
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        print("PASS" if not errors else "FAIL")
    return 0 if not errors else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", choices=["skills", "proposed", "all"], default="all", nargs="?")
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    errors: list[str] = []
    warnings: list[str] = []
    if args.target in {"skills", "all"}:
        e, w = audit_skills(args.strict)
        errors.extend(e)
        warnings.extend(w)
        e, w = audit_routing_eval(args.strict)
        errors.extend(e)
        warnings.extend(w)
    if args.target in {"proposed", "all"}:
        e, w = audit_proposed(args.strict)
        errors.extend(e)
        warnings.extend(w)
    return report(errors, warnings, args.json)


if __name__ == "__main__":
    raise SystemExit(main())
