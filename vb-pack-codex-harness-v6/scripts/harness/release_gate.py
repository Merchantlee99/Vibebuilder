#!/usr/bin/env python3
"""GitHub and release-readiness gate for Codex Harness v6."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

from common import ROOT


TEMPLATE_REQUIRED_FILES = [
    "templates/GitHub-Release.md",
    "templates/Spec-Layer.md",
    "docs/ai/release-governance.md",
    "docs/ai/spec-governance.md",
    ".github/pull_request_template.md",
]

VERSION_RE = re.compile(r"^\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?$")
CHANGELOG_HEADING_RE = re.compile(r"^## \[([^\]]+)\] - \d{4}-\d{2}-\d{2}$", re.MULTILINE)


def run_git(args: list[str]) -> tuple[int, str, str]:
    proc = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()


def read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def latest_changelog_version(path: Path) -> str:
    if not path.exists():
        return ""
    match = CHANGELOG_HEADING_RE.search(path.read_text(encoding="utf-8"))
    return match.group(1).strip() if match else ""


def package_version() -> str:
    package_json = ROOT / "package.json"
    if package_json.exists():
        return str(read_json(package_json).get("version", "")).strip()
    return ""


def check_template() -> tuple[bool, list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    for rel in TEMPLATE_REQUIRED_FILES:
        if not (ROOT / rel).exists():
            errors.append(f"missing required release/spec file: {rel}")

    agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8") if (ROOT / "AGENTS.md").exists() else ""
    for phrase in [
        "GitHub And Release Rules",
        "Intent Spec Rules",
        "release_gate.py",
        "REQ-...",
    ]:
        if phrase not in agents:
            errors.append(f"AGENTS.md missing release/spec phrase: {phrase}")

    workflow = ROOT / ".github" / "workflows" / "harness.yml"
    if workflow.exists() and "release_gate.py --template" not in workflow.read_text(encoding="utf-8"):
        warnings.append("harness workflow does not run release_gate.py --template")

    return not errors, errors, warnings


def check_project(args: argparse.Namespace) -> tuple[bool, list[str], list[str], dict]:
    errors: list[str] = []
    warnings: list[str] = []
    details: dict = {}

    code, branch, stderr = run_git(["status", "--short", "--branch"])
    if code != 0:
        errors.append(f"not a git repository or git status failed: {stderr or branch}")
        return False, errors, warnings, details

    details["status"] = branch
    dirty_lines = [line for line in branch.splitlines()[1:] if line.strip()]
    details["dirty_count"] = len(dirty_lines)
    if dirty_lines and not args.allow_dirty:
        errors.append("worktree has uncommitted changes; pass --allow-dirty only when this is intentional")

    code, current_branch, _stderr = run_git(["branch", "--show-current"])
    details["branch"] = current_branch
    if not current_branch:
        errors.append("detached HEAD is not release-ready")

    code, remote, _stderr = run_git(["remote", "get-url", "origin"])
    details["origin"] = remote
    if code != 0 or not remote:
        warnings.append("origin remote is not configured")

    release_intent = args.release_intent
    version = args.version or package_version() or latest_changelog_version(ROOT / "CHANGELOG.md")
    details["version"] = version

    if release_intent in {"candidate", "publish"}:
        if not version:
            errors.append("release candidate/publish requires --version or a detectable project version")
        elif not VERSION_RE.match(version):
            errors.append(f"version does not look semver-like: {version}")

        changelog_version = latest_changelog_version(ROOT / "CHANGELOG.md")
        details["changelog_version"] = changelog_version
        if not changelog_version:
            errors.append("release candidate/publish requires a top CHANGELOG.md release heading")
        elif version and changelog_version != version:
            errors.append(f"CHANGELOG latest version {changelog_version} does not match {version}")

        pkg_version = package_version()
        details["package_version"] = pkg_version
        if pkg_version and version and pkg_version != version:
            errors.append(f"package.json version {pkg_version} does not match {version}")

    if release_intent == "publish" and version:
        code, tag, _stderr = run_git(["tag", "--list", f"v{version}"])
        details["tag"] = tag
        if tag and not args.allow_existing_tag:
            errors.append(f"tag v{version} already exists; pass --allow-existing-tag only for release-publication retry")
        if not tag and args.require_existing_tag:
            errors.append(f"tag v{version} does not exist")

    return not errors, errors, warnings, details


def emit(ok: bool, errors: list[str], warnings: list[str], details: dict, as_json: bool) -> int:
    if as_json:
        print(json.dumps(
            {"ok": ok, "errors": errors, "warnings": warnings, "details": details},
            indent=2,
            ensure_ascii=False,
        ))
    else:
        for warning in warnings:
            print(f"WARN: {warning}")
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        if details:
            print(json.dumps(details, indent=2, ensure_ascii=False))
        print("PASS" if ok else "FAIL")
    return 0 if ok else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--template", action="store_true", help="Check template release/spec control files.")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--release-intent", choices=["none", "candidate", "publish"], default="none")
    parser.add_argument("--version", default="")
    parser.add_argument("--allow-dirty", action="store_true")
    parser.add_argument("--allow-existing-tag", action="store_true")
    parser.add_argument("--require-existing-tag", action="store_true")
    args = parser.parse_args()

    if args.template:
        ok, errors, warnings = check_template()
        return emit(ok, errors, warnings, {}, args.json)

    ok, errors, warnings, details = check_project(args)
    return emit(ok, errors, warnings, details, args.json)


if __name__ == "__main__":
    raise SystemExit(main())
