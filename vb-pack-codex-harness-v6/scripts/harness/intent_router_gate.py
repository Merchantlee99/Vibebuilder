#!/usr/bin/env python3
"""Validate v6 natural-language intent routing artifacts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from common import ROOT, load_json
from event_log import record_event


DEFAULT_ROUTE = "docs/ai/current/Intent-Routing.json"
TEMPLATE = "templates/Intent-Routing.json"
VALID_TIERS = {"trivial", "normal", "high-risk"}
VALID_MODES = {
    "exploration",
    "spec_authoring",
    "implementation_from_intent",
    "implementation_from_accepted_spec",
    "reverse_spec_review",
    "evidence_mapping",
    "release_audit",
    "team_rule_mining",
    "repository_maintenance",
}
VALID_LAYERS = {"L0", "L1", "L2", "L3"}
VALID_GATES = {
    "intent_router_gate",
    "domain_language_gate",
    "spec_gate",
    "req_evidence_gate",
    "team_rule_mining_gate",
    "rule_promotion_gate",
    "spec_drift_gate",
    "task_profile_gate",
    "implementation_gate",
    "ui_evidence_gate",
    "runtime_evidence_gate",
    "non_web_ui_evidence_gate",
    "strict_gate",
    "quality_gate",
    "simplicity_gate",
    "design_gate",
    "review_gate",
    "release_gate",
    "memory_guard",
}


def load_route(path: Path) -> tuple[dict, list[str]]:
    if not path.exists():
        return {}, [f"missing routing artifact: {path.relative_to(ROOT)}"]
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {}, [f"invalid routing json: {exc}"]
    if not isinstance(data, dict):
        return {}, ["routing artifact must be a JSON object"]
    return data, []


def bool_field(route: dict, key: str) -> bool:
    return route.get(key) is True


def missing_value(value) -> bool:
    return value is None or value == "" or value == []


def validate_route(route: dict, template: bool = False) -> tuple[bool, list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    required = ["schema_version", "task_id", "request_summary", "mode", "tier", "required_gates", "routing_reason", "completion_rule"]
    for key in required:
        if missing_value(route.get(key)):
            errors.append(f"missing {key}")

    mode = route.get("mode")
    tier = route.get("tier")
    if mode and mode not in VALID_MODES:
        errors.append(f"invalid mode: {mode}")
    if tier and tier not in VALID_TIERS:
        errors.append(f"invalid tier: {tier}")

    gates = route.get("required_gates", [])
    if not isinstance(gates, list):
        errors.append("required_gates must be a list")
        gates = []
    for gate in gates:
        if gate not in VALID_GATES:
            errors.append(f"unknown required gate: {gate}")
    if "intent_router_gate" not in gates:
        errors.append("required_gates must include intent_router_gate")

    layers = route.get("spec_layers", [])
    if layers is None:
        layers = []
    if not isinstance(layers, list):
        errors.append("spec_layers must be a list")
        layers = []
    for layer in layers:
        if layer not in VALID_LAYERS:
            errors.append(f"invalid spec layer: {layer}")

    governing = route.get("governing_reqs", [])
    if governing is None:
        governing = []
    if not isinstance(governing, list):
        errors.append("governing_reqs must be a list")
        governing = []

    if tier in {"normal", "high-risk"} and mode not in {"exploration", "spec_authoring", "reverse_spec_review", "team_rule_mining", "repository_maintenance"}:
        if "implementation_gate" not in gates:
            errors.append("normal+ implementation routes must include implementation_gate")
        if "review_gate" not in gates:
            errors.append("normal+ routes must include review_gate")

    if tier == "high-risk" and "strict_gate" not in gates:
        errors.append("high-risk routes must include strict_gate")

    if bool_field(route, "needs_grill_with_docs") and not bool_field(route, "codebase_context"):
        warnings.append("grill-with-docs usually requires codebase_context=true; use grill-me if no codebase exists")
    if bool_field(route, "needs_domain_language") and "domain_language_gate" not in gates:
        errors.append("needs_domain_language requires domain_language_gate")
    if bool_field(route, "needs_spec"):
        if "spec_gate" not in gates:
            errors.append("needs_spec requires spec_gate")
        if "req_evidence_gate" not in gates:
            errors.append("needs_spec requires req_evidence_gate")
        if "L2" not in layers and tier in {"normal", "high-risk"}:
            errors.append("normal+ spec routes require L2 in spec_layers")
    if "L3" in layers and "spec_gate" not in gates:
        errors.append("L3 routes require spec_gate")
    if governing and "req_evidence_gate" not in gates:
        errors.append("governing_reqs require req_evidence_gate")
    if bool_field(route, "needs_team_rule_scan") and "team_rule_mining_gate" not in gates:
        errors.append("needs_team_rule_scan requires team_rule_mining_gate")
    if route.get("team_rule_promotion_allowed") is True and "rule_promotion_gate" not in gates:
        errors.append("team_rule_promotion_allowed requires rule_promotion_gate")

    if template and route.get("schema_version") != 1:
        errors.append("template schema_version must be 1")

    return not errors, errors, warnings


def run_gate(args: argparse.Namespace) -> tuple[bool, list[str], list[str]]:
    path = ROOT / (TEMPLATE if args.template else args.route)
    route, errors = load_route(path)
    if errors:
        return False, errors, []
    ok, route_errors, warnings = validate_route(route, args.template)
    return ok, route_errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--route", default=DEFAULT_ROUTE)
    parser.add_argument("--template", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--warn-only", action="store_true")
    args = parser.parse_args()

    ok, errors, warnings = run_gate(args)
    status = "ok" if ok else ("warning" if args.warn_only else "blocked")
    record_event("intent_router.gate", actor="harness", status=status, errors=errors, warnings=warnings)
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
