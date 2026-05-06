#!/usr/bin/env python3
"""Validate v5 task profiles and objective routing constraints."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from common import ROOT
from event_log import record_event


KINDS = {"bugfix", "feature", "refactor", "ui", "docs", "security", "migration", "runtime-debug", "learning"}
TIERS = {"trivial", "normal", "high-risk"}
SURFACES = {"backend", "frontend", "fullstack", "non-web-ui", "docs", "harness"}
UI_EVIDENCE = {"required", "optional", "not-applicable"}
HIGH_RISK_HINTS = [
    "auth",
    "authentication",
    "authorization",
    "billing",
    "payment",
    "payments",
    "secret",
    "token",
    "migration",
    "infra",
    "delete",
    "destroy",
    "overwrite",
    "restore",
    "compliance",
]
UI_PATH_HINTS = [
    ".tsx",
    ".jsx",
    ".vue",
    ".svelte",
    ".css",
    ".scss",
    ".sass",
    ".less",
    "tailwind",
    "component",
    "page",
    "screen",
]


def load_profile(path: Path) -> tuple[dict, list[str]]:
    if not path.exists():
        return {}, [f"missing task profile: {path}"]
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {}, [f"invalid task profile json: {exc}"]
    return data, []


def has_hint(values: list[str], hints: list[str]) -> bool:
    text = " ".join(values).lower()
    return any(hint in text for hint in hints)


def validate_profile(profile: dict) -> tuple[bool, list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    required = [
        "kind",
        "tier",
        "surface",
        "changed_paths",
        "required_gates",
        "ui_evidence",
        "strict_required",
        "not_applicable_reason",
        "residual_risk",
    ]
    for key in required:
        if key not in profile:
            errors.append(f"missing field: {key}")

    kind = profile.get("kind")
    tier = profile.get("tier")
    surface = profile.get("surface")
    ui_evidence = profile.get("ui_evidence")
    changed_paths = profile.get("changed_paths", [])
    required_gates = profile.get("required_gates", [])

    if kind not in KINDS:
        errors.append(f"invalid kind: {kind}")
    if tier not in TIERS:
        errors.append(f"invalid tier: {tier}")
    if surface not in SURFACES:
        errors.append(f"invalid surface: {surface}")
    if ui_evidence not in UI_EVIDENCE:
        errors.append(f"invalid ui_evidence: {ui_evidence}")
    if not isinstance(changed_paths, list):
        errors.append("changed_paths must be a list")
        changed_paths = []
    if not isinstance(required_gates, list):
        errors.append("required_gates must be a list")
        required_gates = []
    if not isinstance(profile.get("strict_required"), bool):
        errors.append("strict_required must be boolean")

    if tier == "high-risk" and not profile.get("strict_required"):
        errors.append("high-risk profile requires strict_required=true")
    if has_hint(changed_paths, HIGH_RISK_HINTS) and tier != "high-risk":
        warnings.append("changed_paths include high-risk hints but tier is not high-risk")
    if kind in {"security", "migration"} and tier != "high-risk":
        errors.append(f"{kind} work must be high-risk")

    ui_surface = surface in {"frontend", "fullstack", "non-web-ui"} or kind == "ui" or has_hint(changed_paths, UI_PATH_HINTS)
    if ui_surface and ui_evidence == "not-applicable":
        if not profile.get("not_applicable_reason") or not profile.get("residual_risk"):
            errors.append("not-applicable UI evidence requires not_applicable_reason and residual_risk")
    if ui_surface and tier in {"normal", "high-risk"} and ui_evidence == "optional":
        warnings.append("normal+ UI surface usually requires UI evidence")
    if not ui_surface and ui_evidence == "required":
        warnings.append("UI evidence is required for a profile that does not look UI-scoped")

    if tier in {"normal", "high-risk"} and "implementation_gate" not in required_gates:
        warnings.append("normal+ profile should include implementation_gate")
    if ui_evidence == "required" and "ui_evidence_gate" not in required_gates:
        warnings.append("required UI evidence should include ui_evidence_gate")
    if tier == "high-risk" and not any("strict" in gate for gate in required_gates):
        errors.append("high-risk profile requires a strict gate in required_gates")

    return not errors, errors, warnings


def emit(ok: bool, errors: list[str], warnings: list[str], as_json: bool) -> int:
    if as_json:
        print(json.dumps({"ok": ok, "errors": errors, "warnings": warnings}, indent=2, ensure_ascii=False))
    else:
        for warning in warnings:
            print(f"WARN: {warning}")
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        print("PASS" if ok else "FAIL")
    return 0 if ok else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    check = sub.add_parser("check")
    check.add_argument("--profile", default="docs/ai/current/Task-Profile.json")
    check.add_argument("--json", action="store_true")
    check.add_argument("--warn-only", action="store_true")
    template = sub.add_parser("template")
    template.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if args.command == "template":
        profile, load_errors = load_profile(ROOT / "templates" / "Task-Profile.json")
    else:
        profile, load_errors = load_profile(ROOT / args.profile)
    if load_errors:
        return emit(False, load_errors, [], args.json)
    ok, errors, warnings = validate_profile(profile)
    status = "ok" if ok else ("warning" if getattr(args, "warn_only", False) else "blocked")
    record_event("task_profile.gate", actor="harness", status=status, errors=errors, warnings=warnings)
    if getattr(args, "warn_only", False):
        return emit(True, [], errors + warnings, args.json)
    return emit(ok, errors, warnings, args.json)


if __name__ == "__main__":
    raise SystemExit(main())
