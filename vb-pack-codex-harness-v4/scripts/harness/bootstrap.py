#!/usr/bin/env python3
"""Initialize or adopt a Codex Harness v4 template."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RUNTIME = ROOT / "harness" / "runtime.json"

REQUIRED_DIRS = [
    ".codex/agents",
    ".codex/hooks",
    ".agents/skills",
    "harness/context",
    "harness/reviews",
    "harness/telemetry",
    "harness/design",
    "harness/proposed-skills",
    "harness/audits",
    "docs/ai/current",
    "templates",
    "tests",
]

DEFAULT_RUNTIME = {
    "schema_version": 2,
    "framework_version": "v4",
    "deployment_profile": "template",
    "enforcement_mode": "advisory",
    "default_adoption_profile": "creative-daily",
    "default_tier": "normal",
    "state_root": "harness",
    "control_plane_root": ".codex",
    "skills_root": ".agents/skills",
    "review": {
        "normal_requires_independent_review": True,
        "high_risk_requires_independent_review": True,
        "self_review_allowed": False,
    },
    "subagents": {
        "max_threads": 6,
        "max_depth": 1,
        "worker_mode": "worktree",
        "read_only_roles": [
            "pm_strategist",
            "pm_redteam",
            "docs_researcher",
            "code_mapper",
            "task_distributor",
            "reviewer",
            "security_auditor",
            "browser_debugger",
        ],
    },
    "gates": {
        "plan_gate": "normal",
        "review_gate": "normal",
        "finish_gate": "trivial",
        "simplicity_gate": "normal",
        "design_gate": "ui",
    },
    "v4_focus": {
        "purpose": "Daily Codex harness with simplicity discipline and UI/UX design intelligence.",
        "not_a_strict_replacement_for_v3": True,
    },
}


def load_runtime() -> dict:
    if not RUNTIME.exists():
        return dict(DEFAULT_RUNTIME)
    return json.loads(RUNTIME.read_text(encoding="utf-8"))


def save_runtime(runtime: dict) -> None:
    RUNTIME.parent.mkdir(parents=True, exist_ok=True)
    RUNTIME.write_text(json.dumps(runtime, indent=2, sort_keys=False) + "\n", encoding="utf-8")


def is_git_repo() -> bool:
    return (ROOT / ".git").exists()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--adopt-project", action="store_true", help="Switch runtime deployment_profile from template to project.")
    parser.add_argument("--enforce", action="store_true", help="Switch enforcement_mode to enforced. Requires project profile and git repo.")
    args = parser.parse_args()

    for rel in REQUIRED_DIRS:
        (ROOT / rel).mkdir(parents=True, exist_ok=True)

    runtime = load_runtime()

    if args.adopt_project:
        runtime["deployment_profile"] = "project"

    if args.enforce:
        if runtime.get("deployment_profile") != "project":
            raise SystemExit("Cannot enable enforced mode while deployment_profile is not project.")
        if not is_git_repo():
            raise SystemExit("Cannot enable enforced mode before this template is inside a git repository.")
        runtime["enforcement_mode"] = "enforced"

    save_runtime(runtime)
    print(f"bootstrap ok: profile={runtime['deployment_profile']} mode={runtime['enforcement_mode']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
