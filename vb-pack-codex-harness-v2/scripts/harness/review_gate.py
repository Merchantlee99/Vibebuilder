#!/usr/bin/env python3
"""Prepare and finalize independent review artifacts."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from common import ROOT, parse_key_value_lines, nonempty_section, utc_slug


REVIEW_DIR = ROOT / "harness" / "reviews"
TEMPLATE = ROOT / "templates" / "Review.md"


def latest_review() -> Path | None:
    files = sorted(REVIEW_DIR.glob("review-*.md"))
    return files[-1] if files else None


def prepare(args: argparse.Namespace) -> int:
    REVIEW_DIR.mkdir(parents=True, exist_ok=True)
    slug = utc_slug()
    target = REVIEW_DIR / f"review-{slug}.md"
    template = TEMPLATE.read_text(encoding="utf-8")
    body = template
    replacements = {
        "Reviewer:": f"Reviewer: {args.reviewer}",
        "Reviewer-Session:": f"Reviewer-Session: {args.reviewer_session}",
        "Producer:": f"Producer: {args.producer}",
        "Producer-Session:": f"Producer-Session: {args.producer_session}",
        "Tier:": f"Tier: {args.tier}",
    }
    for old, new in replacements.items():
        body = body.replace(old, new, 1)
    body += "\n## Prepared Context\n\n"
    body += f"- Artifact directory: `{args.artifact_dir}`\n"
    if args.changed_file:
        body += "- Changed files:\n"
        for changed in args.changed_file:
            body += f"  - `{changed}`\n"
    body += "- Reviewer must replace `Verdict: pending` before finalize.\n"
    target.write_text(body, encoding="utf-8")
    print(target.relative_to(ROOT))
    return 0


def finalize(args: argparse.Namespace) -> int:
    review = ROOT / args.review_file if args.review_file else latest_review()
    if review is None or not review.exists():
        print("ERROR: review file not found", file=sys.stderr)
        return 1

    text = review.read_text(encoding="utf-8")
    fields = parse_key_value_lines(
        text,
        ["Reviewer", "Reviewer-Session", "Producer", "Producer-Session", "Tier", "Verdict"],
    )

    errors: list[str] = []
    for field, value in fields.items():
        if not value:
            errors.append(f"missing {field}")
    if fields.get("Reviewer") == fields.get("Producer"):
        errors.append("reviewer must differ from producer")
    if fields.get("Reviewer-Session") == fields.get("Producer-Session"):
        errors.append("reviewer session must differ from producer session")
    if fields.get("Verdict", "").lower() not in {"accept", "accept-with-follow-up"}:
        errors.append("verdict must be accept or accept-with-follow-up")
    for heading in ["Scope Reviewed", "Validation Reviewed", "Residual Risk"]:
        if not nonempty_section(text, heading):
            errors.append(f"missing non-empty section: {heading}")
    if "pending" in fields.get("Verdict", "").lower():
        errors.append("pending verdict cannot finalize")
    for changed in args.changed_file:
        if changed not in text:
            errors.append(f"review does not mention changed file: {changed}")

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print(f"review finalized: {review.relative_to(ROOT)}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    prep = sub.add_parser("prepare")
    prep.add_argument("--tier", choices=["normal", "high-risk"], default="normal")
    prep.add_argument("--producer", required=True)
    prep.add_argument("--producer-session", default="main")
    prep.add_argument("--reviewer", default="reviewer")
    prep.add_argument("--reviewer-session", default="reviewer-subagent")
    prep.add_argument("--artifact-dir", default="docs/ai/current")
    prep.add_argument("--changed-file", action="append", default=[])

    fin = sub.add_parser("finalize")
    fin.add_argument("--review-file")
    fin.add_argument("--changed-file", action="append", default=[])

    args = parser.parse_args()
    if args.command == "prepare":
        return prepare(args)
    if args.command == "finalize":
        return finalize(args)
    raise AssertionError(args.command)


if __name__ == "__main__":
    raise SystemExit(main())
