#!/usr/bin/env python3
"""Classify task risk using English/Korean terms and project risk manifest."""

from __future__ import annotations

import argparse
import json

from common import ROOT, load_json
from event_log import record_event


MANIFEST = ROOT / "harness" / "risk_manifest.json"


def classify_text(text: str) -> dict:
    manifest = load_json(MANIFEST, {})
    lowered = text.lower()
    high_terms = manifest.get("high_risk_terms", [])
    normal_terms = manifest.get("normal_terms", [])
    matched_high = [term for term in high_terms if term.lower() in lowered]
    matched_normal = [term for term in normal_terms if term.lower() in lowered]
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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("text", nargs="+")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--log", action="store_true")
    args = parser.parse_args()
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

