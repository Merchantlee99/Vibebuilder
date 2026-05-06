#!/usr/bin/env python3
"""Rubric-based quality checks for plan, review, and validation artifacts."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from common import ROOT, nonempty_section, read_text, tier_at_least
from event_log import record_event


def section_text(text: str, heading: str) -> str:
    match = re.search(rf"^## {re.escape(heading)}\s*$([\s\S]*?)(?=^## |\Z)", text, re.MULTILINE)
    return match.group(1).strip() if match else ""


def has_any(text: str, terms: list[str]) -> bool:
    lowered = text.lower()
    return any(term.lower() in lowered for term in terms)


def check_plan(path: Path, tier: str, template: bool) -> list[str]:
    errors: list[str] = []
    text = read_text(path)
    if not text:
        return [f"missing plan: {path.relative_to(ROOT)}"]
    validation = section_text(text, "Validation")
    rollback = section_text(text, "Rollback")
    if tier_at_least(tier, "normal"):
        if not has_any(validation, ["command", "check", "normal", "failure", "edge", "expected", "검증", "명령", "정상", "실패"]):
            errors.append("plan validation lacks command/check/normal/failure evidence language")
        if not has_any(rollback, ["rollback", "revert", "disable", "recover", "복구", "되돌", "비활성"]):
            errors.append("plan rollback lacks concrete recovery language")
    if tier == "high-risk" and not (has_any(text, ["redteam", "red-team", "pm_redteam", "security", "보안", "리스크"]) or template):
        errors.append("high-risk plan should mention red-team or risk/security review")
    return errors


def check_review(path: Path, tier: str, template: bool) -> list[str]:
    if template:
        return []
    errors: list[str] = []
    text = read_text(path)
    if tier_at_least(tier, "normal") and not text:
        return [f"missing review: {path.relative_to(ROOT)}"]
    if text and not has_any(section_text(text, "Validation Reviewed"), ["command", "test", "check", "검증", "테스트"]):
        errors.append("review validation section does not mention command/test/check evidence")
    if text and not nonempty_section(text, "Residual Risk"):
        errors.append("review residual risk is empty")
    return errors


def check_implement(path: Path, tier: str, template: bool) -> list[str]:
    if template or not tier_at_least(tier, "normal"):
        return []
    text = read_text(path)
    if not text:
        return [f"missing implementation artifact: {path.relative_to(ROOT)}"]
    validation = section_text(text, "Validation")
    if not validation:
        return ["implementation validation is empty"]
    if not has_any(validation, ["command", "exit", "pass", "fail", "not run", "명령", "통과", "실패", "미실행"]):
        return ["implementation validation lacks command/result/not-run evidence"]
    return []


def latest_review_file() -> Path | None:
    files = sorted((ROOT / "harness/reviews").glob("review-*.md"))
    return files[-1] if files else None


def run_quality(args: argparse.Namespace) -> tuple[bool, list[str]]:
    artifact_dir = ROOT / args.artifact_dir
    plan = ROOT / "templates/Plan.md" if args.template else artifact_dir / "Plan.md"
    review = ROOT / "templates/Review.md" if args.template else (ROOT / args.review_file if args.review_file else latest_review_file())
    implement = ROOT / "templates/Implement.md" if args.template else artifact_dir / "Implement.md"

    errors: list[str] = []
    errors.extend(check_plan(plan, args.tier, args.template))
    if review is not None:
        errors.extend(check_review(review, args.tier, args.template))
    elif tier_at_least(args.tier, "normal") and not args.template:
        errors.append("missing review artifact for quality check")
    errors.extend(check_implement(implement, args.tier, args.template))
    return not errors, errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tier", choices=["trivial", "normal", "high-risk"], default="normal")
    parser.add_argument("--artifact-dir", default="docs/ai/current")
    parser.add_argument("--review-file")
    parser.add_argument("--template", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--warn-only", action="store_true")
    args = parser.parse_args()

    ok, errors = run_quality(args)
    status = "ok" if ok else ("warning" if args.warn_only else "blocked")
    record_event("quality.gate", actor="harness", status=status, tier=args.tier, errors=errors)
    if args.json:
        print(json.dumps({"ok": ok or args.warn_only, "errors": errors}, indent=2, ensure_ascii=False))
    else:
        for error in errors:
            print(f"WARN: {error}" if args.warn_only else f"ERROR: {error}", file=sys.stderr)
        print("PASS" if ok or args.warn_only else "FAIL")
    return 0 if ok or args.warn_only else 1


if __name__ == "__main__":
    raise SystemExit(main())

