#!/usr/bin/env python3
"""Score v5 harness readiness against the 9.5 operating target."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from common import ROOT, load_json


CRITERIA = [
    ("native_codex_control_plane", 12, [
        "AGENTS.md",
        ".codex/config.toml",
        ".codex/agents/reviewer.toml",
        ".agents/skills/harness-intake/SKILL.md",
        ".agents/skills/karpathy-engineering/SKILL.md",
        ".agents/skills/ui-ux-design/SKILL.md",
        ".agents/skills/implementation-evidence/SKILL.md",
        ".agents/skills/ui-evidence/SKILL.md",
    ]),
    ("subagent_operating_model", 12, [
        ".codex/agents/pm-strategist.toml",
        ".codex/agents/pm-redteam.toml",
        ".codex/agents/task-distributor.toml",
        "scripts/harness/subagent_planner.py",
    ]),
    ("gates_and_review_enforcement", 16, [
        "scripts/harness/gate.py",
        "scripts/harness/review_gate.py",
        "scripts/harness/quality_gate.py",
        "scripts/harness/simplicity_gate.py",
        "scripts/harness/design_gate.py",
        "scripts/harness/strict_gate.py",
        "scripts/harness/implementation_gate.py",
        "scripts/harness/ui_evidence_gate.py",
        "scripts/harness/task_profile_gate.py",
        "templates/Review.md",
        "templates/Simplicity-Review.md",
        "templates/UI-UX-Brief.md",
        "templates/Design-System.md",
        "templates/UI-Review.md",
        "templates/Task-Profile.json",
        "templates/Visual-Evidence.md",
        "templates/Strict-Adoption.md",
    ]),
    ("long_term_state_and_memory", 10, [
        "harness/runtime.json",
        "harness/strict_policy.json",
        "scripts/harness/event_log.py",
        "scripts/harness/session_index.py",
        "scripts/harness/evidence_log.py",
        "harness/evidence/evidence-matrix.json",
        "docs/ai/SESSION_LOG.md",
        "docs/ai/decisions.md",
        "docs/ai/known-gaps.md",
    ]),
    ("automation_readiness", 8, [
        "scripts/harness/automation_planner.py",
        "templates/Automation-Intent.md",
    ]),
    ("skill_evolution", 8, [
        "scripts/harness/skillify_audit.py",
        "scripts/harness/memory_guard.py",
        ".agents/skills/skillify-proposal/SKILL.md",
        ".agents/skills/memory-curation/SKILL.md",
        "templates/Proposed-Skill.md",
        "templates/Memory-Proposal.md",
    ]),
    ("model_routing_and_gpt55_use", 10, [
        "harness/model_policy.json",
        ".codex/agents/reviewer.toml",
        ".codex/agents/security-auditor.toml",
    ]),
    ("ci_and_project_adoption", 10, [
        ".github/workflows/harness.yml",
        "scripts/harness/adopt_project.py",
        "scripts/harness/self_test.py",
    ]),
    ("session_close_and_operational_docs", 8, [
        "scripts/harness/session_close.py",
        "scripts/harness/harness.py",
        "docs/ai/operations.md",
        "docs/ai/strict-operations.md",
        "docs/ai/v5-final-blueprint.md",
        "docs/ai/design-ops.md",
    ]),
    ("safety_and_optional_hooks", 6, [
        ".codex/hooks/pre_tool_use.py",
        ".codex/hooks/stop.py",
        ".gitignore",
    ]),
]


def file_score(files: list[str]) -> tuple[int, list[str]]:
    missing = [path for path in files if not (ROOT / path).exists()]
    if not missing:
        return 100, []
    present = len(files) - len(missing)
    return int((present / len(files)) * 100), missing


def command_ok(command: list[str]) -> bool:
    proc = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)
    return proc.returncode == 0


def score() -> dict:
    items = []
    total = 0.0
    possible = 0
    for name, weight, files in CRITERIA:
        pct, missing = file_score(files)
        earned = weight * pct / 100
        total += earned
        possible += weight
        items.append({"name": name, "weight": weight, "score": round(earned, 2), "missing": missing})

    checks = {
        "self_test": command_ok([sys.executable, "scripts/harness/self_test.py"]),
        "skillify_audit": command_ok([sys.executable, "scripts/harness/skillify_audit.py", "all"]),
        "automation_audit": command_ok([sys.executable, "scripts/harness/automation_planner.py", "audit"]),
        "quality_gate": command_ok([sys.executable, "scripts/harness/quality_gate.py", "--tier", "high-risk", "--template"]),
        "simplicity_gate": command_ok([sys.executable, "scripts/harness/simplicity_gate.py", "--template"]),
        "design_gate": command_ok([sys.executable, "scripts/harness/design_gate.py", "--template"]),
        "strict_gate": command_ok([sys.executable, "scripts/harness/strict_gate.py", "--template"]),
        "task_profile_gate": command_ok([sys.executable, "scripts/harness/task_profile_gate.py", "template"]),
        "implementation_gate": command_ok([sys.executable, "scripts/harness/implementation_gate.py", "--template"]),
        "ui_evidence_gate": command_ok([sys.executable, "scripts/harness/ui_evidence_gate.py", "--template"]),
        "memory_guard": command_ok([sys.executable, "scripts/harness/memory_guard.py", "audit"]),
        "risk_classifier": command_ok([sys.executable, "scripts/harness/risk_classifier.py", "권한 결제 수정"]),
        "risk_manifest": command_ok([sys.executable, "scripts/harness/risk_classifier.py", "--audit-manifest"]),
        "event_log_verify": command_ok([sys.executable, "scripts/harness/event_log.py", "verify"]),
    }
    failed_checks = [name for name, ok in checks.items() if not ok]
    if failed_checks:
        total -= 5 * len(failed_checks)

    model_policy = load_json(ROOT / "harness/model_policy.json", {})
    if model_policy.get("frontier_model") != "gpt-5.5":
        total -= 5
        failed_checks.append("frontier_model_not_gpt_5_5")

    total = max(0.0, min(float(possible), total))
    return {
        "score": round(total, 2),
        "max_score": possible,
        "ratio": round(total / possible, 4),
        "items": items,
        "checks": checks,
        "failed_checks": failed_checks,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--min-score", type=float, default=0)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    result = score()
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"score: {result['score']}/{result['max_score']} ({result['ratio'] * 10:.2f}/10)")
        for item in result["items"]:
            suffix = f" missing={item['missing']}" if item["missing"] else ""
            print(f"- {item['name']}: {item['score']}/{item['weight']}{suffix}")
        if result["failed_checks"]:
            print(f"failed checks: {', '.join(result['failed_checks'])}")

    if args.min_score and result["score"] < args.min_score:
        return 1
    return 0 if not result["failed_checks"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
