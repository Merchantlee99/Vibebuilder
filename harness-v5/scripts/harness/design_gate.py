#!/usr/bin/env python3
"""Check UI/UX design artifacts and pre-delivery quality evidence."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from common import ROOT, nonempty_section, read_text
from event_log import record_event


UI_TERMS = [
    "ui",
    "ux",
    "frontend",
    "front-end",
    "landing",
    "dashboard",
    "component",
    "form",
    "modal",
    "button",
    "responsive",
    "accessibility",
    "design",
    "mobile",
    "화면",
    "디자인",
    "프론트",
    "반응형",
    "접근성",
]

REQUIRED_ARTIFACTS = {
    "UI-UX-Brief.md": [
        "User Goal",
        "Product Intent",
        "Primary Action",
        "Visual Direction",
        "Responsive Strategy",
        "Accessibility Requirements",
    ],
    "Design-System.md": [
        "Design Principles",
        "Color Tokens",
        "Typography",
        "Spacing",
        "Components",
        "Accessibility",
    ],
    "UI-Review.md": [
        "Scope Reviewed",
        "Accessibility",
        "Responsive Behavior",
        "Interaction States",
        "Visual Consistency",
        "Anti-Patterns Found",
        "Residual Risk",
    ],
}


def likely_ui_scope(args: argparse.Namespace) -> bool:
    if args.ui:
        return True
    text = " ".join(args.context or [])
    if text:
        lowered = text.lower()
        return any(term in lowered for term in UI_TERMS)
    artifact_dir = ROOT / args.artifact_dir
    if not artifact_dir.exists():
        return False
    combined = "\n".join(path.read_text(encoding="utf-8", errors="ignore") for path in artifact_dir.glob("*.md"))
    lowered = combined.lower()
    return any(term in lowered for term in UI_TERMS)


def template_path(name: str) -> Path:
    mapping = {
        "UI-UX-Brief.md": ROOT / "templates" / "UI-UX-Brief.md",
        "Design-System.md": ROOT / "templates" / "Design-System.md",
        "UI-Review.md": ROOT / "templates" / "UI-Review.md",
    }
    return mapping[name]


def check_artifact(path: Path, headings: list[str]) -> list[str]:
    errors: list[str] = []
    text = read_text(path)
    if not text:
        return [f"missing artifact: {path.relative_to(ROOT)}"]
    for heading in headings:
        if not nonempty_section(text, heading):
            errors.append(f"{path.relative_to(ROOT)} missing non-empty section: {heading}")
    return errors


def run_gate(args: argparse.Namespace) -> tuple[bool, list[str], list[str]]:
    warnings: list[str] = []
    errors: list[str] = []
    if not args.template and not likely_ui_scope(args):
        return True, errors, ["no UI/UX scope detected"]

    base = ROOT / args.artifact_dir
    for name, headings in REQUIRED_ARTIFACTS.items():
        path = template_path(name) if args.template else base / name
        errors.extend(check_artifact(path, headings))

    if not args.template:
        review_text = read_text(base / "UI-Review.md").lower()
        for term in ["accessibility", "responsive", "interaction", "anti-pattern", "contrast", "focus"]:
            if term not in review_text:
                warnings.append(f"UI review should mention {term}")

    return not errors, errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-dir", default="docs/ai/current")
    parser.add_argument("--context", action="append", default=[])
    parser.add_argument("--ui", action="store_true")
    parser.add_argument("--template", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--warn-only", action="store_true")
    args = parser.parse_args()

    ok, errors, warnings = run_gate(args)
    status = "ok" if ok else ("warning" if args.warn_only else "blocked")
    record_event("design.gate", actor="harness", status=status, errors=errors, warnings=warnings)

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
