#!/usr/bin/env python3
"""Classify task risk using English/Korean terms and project risk manifest."""

from __future__ import annotations

import argparse
import json
import re

from common import ROOT, load_json
from event_log import record_event


MANIFEST = ROOT / "harness" / "risk_manifest.json"
BASELINE = ROOT / "scripts" / "harness" / "risk_manifest_baseline.json"


def is_ascii_term(term: str) -> bool:
    return all(ord(ch) < 128 for ch in term)


def english_term_matches(term: str, lowered: str) -> bool:
    if len(term) <= 3:
        pattern = rf"(?<![a-z0-9_]){re.escape(term.lower())}(?![a-z0-9_])"
    else:
        pattern = rf"\b{re.escape(term.lower())}\b"
    return re.search(pattern, lowered) is not None


def term_matches(term: str, lowered: str) -> bool:
    if is_ascii_term(term):
        return english_term_matches(term, lowered)
    return term.lower() in lowered


def classify_text(text: str) -> dict:
    manifest = load_json(MANIFEST, {})
    lowered = text.lower()
    high_terms = manifest.get("high_risk_terms", [])
    normal_terms = manifest.get("normal_terms", [])
    matched_high = [term for term in high_terms if term_matches(term, lowered)]
    matched_normal = [term for term in normal_terms if term_matches(term, lowered)]
    if matched_high:
        tier = "high-risk"
    elif matched_normal:
        tier = "normal"
    else:
        tier = "trivial"
    confidence = "high" if matched_high or matched_normal else "low"
    return {
        "tier": tier,
        "confidence": confidence,
        "matched_high": matched_high,
        "matched_normal": matched_normal,
    }


def audit_manifest() -> tuple[bool, list[str]]:
    manifest = load_json(MANIFEST, {})
    baseline = load_json(BASELINE, {})
    configured = set(manifest.get("high_risk_terms", []))
    required = set(baseline.get("required_high_risk_terms", []))
    errors = [f"missing required high-risk term: {term}" for term in sorted(required - configured)]
    return not errors, errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("text", nargs="*")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--log", action="store_true")
    parser.add_argument("--audit-manifest", action="store_true")
    args = parser.parse_args()
    if args.audit_manifest:
        ok, errors = audit_manifest()
        if args.json:
            print(json.dumps({"ok": ok, "errors": errors}, indent=2, ensure_ascii=False))
        else:
            for error in errors:
                print(f"ERROR: {error}")
            print("risk manifest ok" if ok else "risk manifest failed")
        return 0 if ok else 1
    if not args.text:
        parser.error("text is required unless --audit-manifest is used")
    result = classify_text(" ".join(args.text))
    if args.log:
        record_event("risk.classify", actor="harness", status=result["tier"], **result)
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(result["tier"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
