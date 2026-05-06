#!/usr/bin/env python3
"""Audit Codex Harness v5 strict/high-risk readiness."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

from common import ROOT, load_json
from event_log import verify_events


RUNTIME = ROOT / "harness" / "runtime.json"
STRICT_POLICY = ROOT / "harness" / "strict_policy.json"
CONFIG = ROOT / ".codex" / "config.toml"


def read_toml_bool(path: Path, key: str) -> bool | None:
    if not path.exists():
        return None
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        left, right = [part.strip() for part in line.split("=", 1)]
        if left == key:
            if right.lower() == "true":
                return True
            if right.lower() == "false":
                return False
    return None


def command_ok(command: list[str]) -> bool:
    proc = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)
    return proc.returncode == 0


def audit(args: argparse.Namespace) -> dict:
    runtime = load_json(RUNTIME, {})
    policy = load_json(STRICT_POLICY, {})
    profile = args.profile or runtime.get("default_adoption_profile", "implementation-first-evidence")
    profiles = policy.get("profiles", {})
    profile_policy = profiles.get(profile, {})

    errors: list[str] = []
    warnings: list[str] = []

    if profile not in profiles:
        errors.append(f"strict profile is not configured: {profile}")

    for rel in policy.get("required_static_assets", []):
        if not (ROOT / rel).exists():
            errors.append(f"missing strict asset: {rel}")

    hooks_enabled = read_toml_bool(CONFIG, "codex_hooks")
    if profile_policy.get("hooks_required") and hooks_enabled is not True:
        errors.append(".codex/config.toml must set codex_hooks = true for this strict profile")

    if runtime.get("framework_version") != "v5":
        errors.append("runtime framework_version must be v5")
    if runtime.get("default_adoption_profile") not in profiles:
        errors.append("runtime default_adoption_profile must exist in strict_policy profiles")
    if runtime.get("review", {}).get("high_risk_requires_hmac_approval") is not True:
        errors.append("high-risk review must require HMAC approval in v5 strict policy")
    if runtime.get("review", {}).get("prepared_event_required") is not True:
        errors.append("prepared review event must be required in v5 strict policy")

    events_ok, event_errors = verify_events()
    if not events_ok:
        errors.extend(f"event log: {error}" for error in event_errors)

    if not command_ok([sys.executable, "scripts/harness/risk_classifier.py", "--audit-manifest"]):
        errors.append("risk manifest audit failed")
    if not command_ok([sys.executable, "scripts/harness/skillify_audit.py", "all"]):
        errors.append("skillify audit failed")
    if not command_ok([sys.executable, "scripts/harness/automation_planner.py", "audit"]):
        errors.append("automation audit failed")

    if not args.template:
        if runtime.get("deployment_profile") != "project":
            warnings.append("deployment_profile is not project")
        if profile_policy.get("enforcement_mode") == "enforced" and runtime.get("enforcement_mode") != "enforced":
            errors.append("strict project adoption requires enforcement_mode = enforced")
        if profile_policy.get("enforcement_mode") == "enforced" and not (ROOT / ".git").exists():
            errors.append("strict enforced mode requires a git repository")
        if profile_policy.get("high_risk_hmac_required") and args.require_hmac_env and not os.environ.get(args.require_hmac_env):
            errors.append(f"missing required HMAC env: {args.require_hmac_env}")
        if profile_policy.get("branch_protection_required") and not (ROOT / "docs" / "ai" / "strict-operations.md").exists():
            errors.append("missing branch protection operating instructions")
        if profile_policy.get("offsite_backup_required"):
            warnings.append("off-site backup must be configured outside this local template")

    return {
        "ok": not errors,
        "profile": profile,
        "template": args.template,
        "errors": errors,
        "warnings": warnings,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=["implementation-first-evidence", "solo", "strict", "team", "production"])
    parser.add_argument("--template", action="store_true")
    parser.add_argument("--require-hmac-env")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    result = audit(args)
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        for warning in result["warnings"]:
            print(f"WARN: {warning}")
        for error in result["errors"]:
            print(f"ERROR: {error}", file=sys.stderr)
        print("strict gate ok" if result["ok"] else "strict gate failed")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
