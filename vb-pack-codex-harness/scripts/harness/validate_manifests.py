#!/usr/bin/env python3
"""Parse and validate harness manifest schemas."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from manifest_loader import ManifestError, expect_type, load as load_manifest
else:  # pragma: no cover - package import path
    from .manifest_loader import ManifestError, expect_type, load as load_manifest


def repo_root() -> Path:
    current = Path.cwd().resolve()
    for candidate in (current, *current.parents):
        if (candidate / ".codex").exists() or (candidate / ".git").exists():
            return candidate
    return current


def _validate_capability_routing(data: dict) -> None:
    expect_type(data, dict, "capability-routing")
    expect_type(data.get("defaults"), dict, "capability-routing.defaults")
    routes = data.get("routes")
    expect_type(routes, dict, "capability-routing.routes")
    for key, value in routes.items():
        expect_type(value, dict, f"capability-routing.routes.{key}")
        for field in ("tool", "role", "note"):
            if field not in value:
                raise ManifestError(f"capability-routing.routes.{key}: missing {field}")


def _validate_subagents(data: dict) -> None:
    roles = data.get("roles")
    expect_type(roles, dict, "subagents.roles")
    for role, value in roles.items():
        expect_type(value, dict, f"subagents.roles.{role}")
        for field in ("can_delegate", "write_scope", "default_mode", "purpose"):
            if field not in value:
                raise ManifestError(f"subagents.roles.{role}: missing {field}")
    defaults = data.get("defaults")
    expect_type(defaults, dict, "subagents.defaults")
    for field in ("shared_read_scope", "protected_paths"):
        expect_type(defaults.get(field), list, f"subagents.defaults.{field}")
    parallelism = data.get("parallelism")
    expect_type(parallelism, dict, "subagents.parallelism")
    for field in ("max_active_workers", "ownership_state"):
        if field not in parallelism:
            raise ManifestError(f"subagents.parallelism: missing {field}")
    required_contract = data.get("required_contract")
    expect_type(required_contract, list, "subagents.required_contract")
    handoff = data.get("handoff")
    expect_type(handoff, dict, "subagents.handoff")
    for role in ("explorer", "worker", "reviewer"):
        expect_type(handoff.get(role), list, f"subagents.handoff.{role}")
    expect_type(data.get("rules"), list, "subagents.rules")


def _validate_review_matrix(data: dict) -> None:
    tiers = data.get("tiers")
    expect_type(tiers, dict, "review-matrix.tiers")
    for required_tier in ("trivial", "normal", "high-risk"):
        if required_tier not in tiers:
            raise ManifestError(f"review-matrix.tiers missing {required_tier}")
        tier_data = tiers[required_tier]
        expect_type(tier_data, dict, f"review-matrix.tiers.{required_tier}")
        expect_type(tier_data.get("required_artifacts"), list, f"review-matrix.tiers.{required_tier}.required_artifacts")
        if "required_review" not in tier_data:
            raise ManifestError(f"review-matrix.tiers.{required_tier}: missing required_review")
    expect_type(data.get("review_focus"), list, "review-matrix.review_focus")


def _validate_mode_policy(data: dict) -> None:
    profiles = data.get("profiles")
    expect_type(profiles, dict, "mode-policy.profiles")
    for required_profile in ("template", "project"):
        if required_profile not in profiles:
            raise ManifestError(f"mode-policy.profiles missing {required_profile}")
        profile_data = profiles[required_profile]
        expect_type(profile_data, dict, f"mode-policy.profiles.{required_profile}")
        expect_type(
            profile_data.get("allowed_runtime_modes"),
            list,
            f"mode-policy.profiles.{required_profile}.allowed_runtime_modes",
        )
        use_for = profile_data.get("use_for")
        if use_for is not None:
            expect_type(use_for, list, f"mode-policy.profiles.{required_profile}.use_for")
        enforced_requires = profile_data.get("enforced_requires")
        if enforced_requires is not None:
            expect_type(
                enforced_requires,
                list,
                f"mode-policy.profiles.{required_profile}.enforced_requires",
            )
    modes = data.get("modes")
    expect_type(modes, dict, "mode-policy.modes")
    for required_mode in ("local", "worktree", "cloud"):
        if required_mode not in modes:
            raise ManifestError(f"mode-policy.modes missing {required_mode}")
        mode_data = modes[required_mode]
        expect_type(mode_data, dict, f"mode-policy.modes.{required_mode}")
        expect_type(mode_data.get("use_for"), list, f"mode-policy.modes.{required_mode}.use_for")
        expect_type(mode_data.get("avoid_for"), list, f"mode-policy.modes.{required_mode}.avoid_for")


def _validate_automation_policy(data: dict) -> None:
    expect_type(data.get("defaults"), dict, "automation-policy.defaults")
    expect_type(data.get("create_when"), list, "automation-policy.create_when")
    expect_type(data.get("rules"), list, "automation-policy.rules")
    avoid_when = data.get("avoid_when")
    if avoid_when is not None:
        expect_type(avoid_when, list, "automation-policy.avoid_when")
    signals = data.get("signals")
    expect_type(signals, dict, "automation-policy.signals")
    recommended_loops = data.get("recommended_loops")
    expect_type(recommended_loops, dict, "automation-policy.recommended_loops")
    for loop_name, payload in recommended_loops.items():
        expect_type(payload, dict, f"automation-policy.recommended_loops.{loop_name}")
        for field in ("kind", "destination", "cadence_hint", "expected_output", "skip_condition"):
            if field not in payload:
                raise ManifestError(f"automation-policy.recommended_loops.{loop_name}: missing {field}")
    contract = data.get("intent_contract")
    expect_type(contract, dict, "automation-policy.intent_contract")
    expect_type(contract.get("required"), list, "automation-policy.intent_contract.required")


def _validate_evolution_policy(data: dict) -> None:
    for section in ("prefetch", "sync_from_events", "skill_auto_gen", "insights"):
        expect_type(data.get(section), dict, f"evolution-policy.{section}")


VALIDATORS = {
    "capability-routing.yaml": _validate_capability_routing,
    "subagents.yaml": _validate_subagents,
    "review-matrix.yaml": _validate_review_matrix,
    "mode-policy.yaml": _validate_mode_policy,
    "automation-policy.yaml": _validate_automation_policy,
    "evolution-policy.yaml": _validate_evolution_policy,
}


def validate_all(root: Path) -> dict[str, str]:
    results: dict[str, str] = {}
    manifest_dir = root / ".codex" / "manifests"
    for name, validator in VALIDATORS.items():
        path = manifest_dir / name
        if not path.exists():
            raise ManifestError(f"missing manifest: {path}")
        data = load_manifest(path)
        validator(data)
        results[name] = "ok"
    return results


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    root = repo_root()
    try:
        results = validate_all(root)
    except ManifestError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(results, indent=2, ensure_ascii=False))
    else:
        for name, status in results.items():
            print(f"{name}: {status}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
