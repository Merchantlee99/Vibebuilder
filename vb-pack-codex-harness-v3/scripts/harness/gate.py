#!/usr/bin/env python3
"""Deterministic gates for Codex Harness v3."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from risk_classifier import classify_text


ROOT = Path(__file__).resolve().parents[2]
RUNTIME = ROOT / "harness" / "runtime.json"

TIER_ORDER = {"trivial": 0, "normal": 1, "high-risk": 2}

REQUIRED_CONTROL_FILES = [
    "AGENTS.md",
    "README.md",
    "ETHOS.md",
    ".codex/config.toml",
    ".codex/hooks.json",
    ".codex/agents/pm-strategist.toml",
    ".codex/agents/pm-redteam.toml",
    ".codex/agents/docs-researcher.toml",
    ".codex/agents/code-mapper.toml",
    ".codex/agents/task-distributor.toml",
    ".codex/agents/reviewer.toml",
    ".codex/agents/security-auditor.toml",
    ".codex/agents/browser-debugger.toml",
    ".agents/skills/harness-intake/SKILL.md",
    ".agents/skills/product-planning/SKILL.md",
    ".agents/skills/plan-before-change/SKILL.md",
    ".agents/skills/critical-review/SKILL.md",
    ".agents/skills/close-session/SKILL.md",
    ".agents/skills/skillify-proposal/SKILL.md",
    "harness/runtime.json",
    "harness/strict_policy.json",
    "harness/risk_manifest.json",
    "scripts/harness/review_gate.py",
    "scripts/harness/subagent_planner.py",
    "scripts/harness/automation_planner.py",
    "scripts/harness/skillify_audit.py",
    "scripts/harness/risk_classifier.py",
    "scripts/harness/quality_gate.py",
    "scripts/harness/strict_gate.py",
]

MUTABLE_CODEX_PATHS = [
    ".codex/runtime.json",
    ".codex/context",
    ".codex/reviews",
    ".codex/telemetry",
    ".codex/audits",
]


class GateResult:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    @property
    def ok(self) -> bool:
        return not self.errors

    def error(self, message: str) -> None:
        self.errors.append(message)

    def warn(self, message: str) -> None:
        self.warnings.append(message)

    def extend(self, other: "GateResult") -> None:
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)


def load_runtime(result: GateResult) -> dict:
    if not RUNTIME.exists():
        result.error("Missing harness/runtime.json.")
        return {}
    try:
        return json.loads(RUNTIME.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        result.error(f"Invalid harness/runtime.json: {exc}")
        return {}


def tier_at_least(tier: str, minimum: str) -> bool:
    return TIER_ORDER[tier] >= TIER_ORDER[minimum]


def nonempty_section(text: str, heading: str) -> bool:
    pattern = rf"^## {re.escape(heading)}\s*$([\s\S]*?)(?=^## |\Z)"
    match = re.search(pattern, text, re.MULTILINE)
    if not match:
        return False
    body = match.group(1).strip()
    if not body:
        return False
    placeholders = {"tbd", "todo", "n/a", "none", "-"}
    return body.lower() not in placeholders


def preflight(_: argparse.Namespace) -> GateResult:
    result = GateResult()
    runtime = load_runtime(result)

    for rel in REQUIRED_CONTROL_FILES:
        if not (ROOT / rel).exists():
            result.error(f"Missing required file: {rel}")

    for rel in MUTABLE_CODEX_PATHS:
        if (ROOT / rel).exists():
            result.error(f"Mutable state must not live under .codex: {rel}")

    profile = runtime.get("deployment_profile")
    mode = runtime.get("enforcement_mode")
    if profile == "template" and mode == "enforced":
        result.error("Template profile cannot use enforced mode.")
    if mode == "enforced" and not (ROOT / ".git").exists():
        result.error("Enforced mode requires a git repository.")

    if not (ROOT / "harness").exists():
        result.error("Missing harness state root.")

    return result


def plan_gate(args: argparse.Namespace) -> GateResult:
    result = GateResult()
    if not tier_at_least(args.tier, "normal"):
        return result

    plan = ROOT / ("templates/Plan.md" if args.template else f"{args.artifact_dir}/Plan.md")
    if not plan.exists():
        result.error(f"Missing plan artifact: {plan.relative_to(ROOT)}")
        return result

    text = plan.read_text(encoding="utf-8")
    for heading in ["Goal", "Scope", "Validation", "Rollback"]:
        if not nonempty_section(text, heading):
            result.error(f"Plan is missing non-empty section: {heading}")

    if args.tier == "high-risk" and not nonempty_section(text, "Open Risks"):
        result.error("High-risk plan requires non-empty Open Risks.")

    return result


def scope_gate(args: argparse.Namespace) -> GateResult:
    result = GateResult()
    claims = ROOT / "harness" / "context" / "ownership-claims.json"
    if claims.exists():
        try:
            data = json.loads(claims.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            result.error(f"Invalid ownership claims file: {exc}")
            data = []
        active = [claim for claim in data if claim.get("status") == "active"]
        for idx, left in enumerate(active):
            for right in active[idx + 1:]:
                if path_list_overlap(left.get("write_scope", []), right.get("write_scope", [])):
                    result.error(f"Ownership conflict: {left.get('owner')} overlaps {right.get('owner')}")

    dispatch = ROOT / ("templates/Subagent-Dispatch.yaml" if args.template else f"{args.artifact_dir}/Subagent-Dispatch.yaml")
    if args.template and not dispatch.exists():
        result.error("Missing templates/Subagent-Dispatch.yaml.")
        return result
    if not args.template and tier_at_least(args.tier, "normal") and not dispatch.exists():
        result.warn("No Subagent-Dispatch.yaml found. This is acceptable only if no subagents are used.")
        return result
    if dispatch.exists():
        text = dispatch.read_text(encoding="utf-8")
        for key in ["role:", "goal:", "mode:", "write_scope:", "stop_condition:", "expected_artifact:"]:
            if key not in text:
                result.error(f"Subagent dispatch missing key: {key}")
    return result


def path_list_overlap(left: list[str], right: list[str]) -> bool:
    for a in left:
        for b in right:
            a_norm = str(a).strip().rstrip("/")
            b_norm = str(b).strip().rstrip("/")
            if not a_norm or not b_norm:
                continue
            if a_norm == b_norm or a_norm.startswith(b_norm + "/") or b_norm.startswith(a_norm + "/"):
                return True
    return False


def latest_review_file() -> Path | None:
    files = sorted((ROOT / "harness/reviews").glob("review-*.md"))
    return files[-1] if files else None


def review_gate(args: argparse.Namespace) -> GateResult:
    result = GateResult()
    if not tier_at_least(args.tier, "normal"):
        return result

    if args.template:
        review = ROOT / "templates/Review.md"
    elif args.review_file:
        review = ROOT / args.review_file
    else:
        review = latest_review_file()
        if review is None:
            result.error("Missing independent review artifact for normal+ work.")
            return result

    if not review.exists():
        result.error(f"Missing review artifact: {review}")
        return result

    text = review.read_text(encoding="utf-8")
    fields = {}
    for field in ["Reviewer", "Reviewer-Session", "Producer", "Producer-Session", "Verdict"]:
        match = re.search(rf"^{re.escape(field)}:\s*(.*)$", text, re.MULTILINE)
        value = match.group(1).strip() if match else ""
        fields[field] = value
        if not value and not args.template:
            result.error(f"Review missing required field: {field}")

    if not args.template:
        if fields["Reviewer"] == fields["Producer"]:
            result.error("Reviewer must differ from Producer.")
        if fields["Reviewer-Session"] == fields["Producer-Session"]:
            result.error("Reviewer-Session must differ from Producer-Session.")
        verdict = fields["Verdict"].lower()
        if verdict not in {"accept", "accept-with-follow-up"}:
            result.error("Review verdict must be accept or accept-with-follow-up.")

    for heading in ["Scope Reviewed", "Validation Reviewed", "Residual Risk"]:
        if not nonempty_section(text, heading) and not args.template:
            result.error(f"Review missing non-empty section: {heading}")

    return result


def finish_gate(args: argparse.Namespace) -> GateResult:
    result = GateResult()
    result.extend(preflight(args))
    result.extend(plan_gate(args))
    result.extend(scope_gate(args))
    result.extend(review_gate(args))

    if not args.template and tier_at_least(args.tier, "normal"):
        implement = ROOT / f"{args.artifact_dir}/Implement.md"
        if not implement.exists():
            result.error(f"Missing implementation artifact: {implement.relative_to(ROOT)}")
        else:
            text = implement.read_text(encoding="utf-8")
            if not nonempty_section(text, "Validation"):
                result.error("Implement.md requires non-empty Validation before completion.")

    return result


def classify(args: argparse.Namespace) -> GateResult:
    result = GateResult()
    risk = classify_text(" ".join(args.text))
    if args.json:
        print(json.dumps(risk, indent=2, ensure_ascii=False))
    else:
        print(risk["tier"])
    return result


COMMANDS = {
    "preflight": preflight,
    "plan-gate": plan_gate,
    "scope-gate": scope_gate,
    "review-gate": review_gate,
    "finish-gate": finish_gate,
    "all": finish_gate,
    "classify": classify,
}


def emit(result: GateResult, as_json: bool) -> int:
    if as_json:
        print(json.dumps({"ok": result.ok, "errors": result.errors, "warnings": result.warnings}, indent=2))
    else:
        for warning in result.warnings:
            print(f"WARN: {warning}")
        for error in result.errors:
            print(f"ERROR: {error}", file=sys.stderr)
        print("PASS" if result.ok else "FAIL")
    return 0 if result.ok else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=sorted(COMMANDS))
    parser.add_argument("text", nargs="*", help="Text to classify when command is classify.")
    parser.add_argument("--tier", choices=sorted(TIER_ORDER), default="normal")
    parser.add_argument("--artifact-dir", default="docs/ai/current")
    parser.add_argument("--review-file")
    parser.add_argument("--template", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    result = COMMANDS[args.command](args)
    if args.command == "classify":
        return 0 if result.ok else 1
    return emit(result, args.json)


if __name__ == "__main__":
    raise SystemExit(main())
