#!/usr/bin/env python3
"""Adopt this harness template into a real project."""

from __future__ import annotations

import argparse
import sys

from common import ROOT, load_json, write_json


RUNTIME = ROOT / "harness" / "runtime.json"
CONFIG = ROOT / ".codex" / "config.toml"
CI = ROOT / ".github" / "workflows" / "harness.yml"
STRICT_POLICY = ROOT / "harness" / "strict_policy.json"


def set_hooks_enabled(enabled: bool) -> None:
    text = CONFIG.read_text(encoding="utf-8")
    if "codex_hooks = " in text:
        text = text.replace("codex_hooks = false", f"codex_hooks = {str(enabled).lower()}")
        text = text.replace("codex_hooks = true", f"codex_hooks = {str(enabled).lower()}")
    else:
        text += f"\n[features]\ncodex_hooks = {str(enabled).lower()}\n"
    CONFIG.write_text(text, encoding="utf-8")


def check(args: argparse.Namespace) -> int:
    errors: list[str] = []
    warnings: list[str] = []

    if not (ROOT / ".git").exists():
        warnings.append("not a git repository; enforced mode and CI branch protection cannot be verified here")
    if not RUNTIME.exists():
        errors.append("missing harness/runtime.json")
    if not CONFIG.exists():
        errors.append("missing .codex/config.toml")
    if not CI.exists():
        warnings.append("missing .github/workflows/harness.yml")

    runtime = load_json(RUNTIME, {})
    policy = load_json(STRICT_POLICY, {})
    active_profile = runtime.get("active_profile") or runtime.get("default_adoption_profile")
    profile = runtime.get("deployment_profile")
    mode = runtime.get("enforcement_mode")
    if profile == "template":
        warnings.append("deployment_profile is still template")
    if mode == "enforced" and not (ROOT / ".git").exists():
        errors.append("enforced mode requires git repository")
    if active_profile and active_profile not in policy.get("profiles", {}):
        errors.append(f"unknown active/default profile: {active_profile}")

    for warning in warnings:
        print(f"WARN: {warning}")
    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)
    if errors:
        return 1
    if args.strict and warnings:
        return 1
    print("adoption check ok")
    return 0


def write(args: argparse.Namespace) -> int:
    runtime = load_json(RUNTIME, {})
    runtime["deployment_profile"] = "project"
    if args.profile:
        runtime["active_profile"] = args.profile
    strict_profiles = {"strict", "team", "production"}
    should_enforce = args.enforce or args.profile in strict_profiles
    if should_enforce:
        if not (ROOT / ".git").exists():
            print("ERROR: enforced/strict adoption requires a git repository", file=sys.stderr)
            return 1
        runtime["enforcement_mode"] = "enforced"
    if args.profile == "solo" and runtime.get("enforcement_mode") != "enforced":
        runtime["enforcement_mode"] = "advisory"
    write_json(RUNTIME, runtime)
    if args.enable_hooks or args.profile in {"solo", "strict", "team", "production"}:
        set_hooks_enabled(True)
    print(
        "adopted project: "
        f"profile={runtime.get('deployment_profile')} "
        f"active_profile={runtime.get('active_profile', runtime.get('default_adoption_profile'))} "
        f"mode={runtime.get('enforcement_mode')}"
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Only check adoption readiness.")
    parser.add_argument("--strict", action="store_true", help="Treat warnings as failures for --check.")
    parser.add_argument("--write", action="store_true", help="Switch runtime deployment_profile to project.")
    parser.add_argument("--enforce", action="store_true", help="Enable enforced mode. Requires git repository.")
    parser.add_argument("--enable-hooks", action="store_true", help="Enable codex_hooks in .codex/config.toml.")
    parser.add_argument(
        "--profile",
        choices=["solo", "strict", "team", "production"],
        help="Apply a v3 adoption profile. strict/team/production imply enforced mode and hooks.",
    )
    args = parser.parse_args()

    if args.write:
        return write(args)
    return check(args)


if __name__ == "__main__":
    raise SystemExit(main())
