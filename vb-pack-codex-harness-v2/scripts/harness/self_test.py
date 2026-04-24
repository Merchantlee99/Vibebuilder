#!/usr/bin/env python3
"""Structural self-test for Codex Harness v2."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

REQUIRED_FILES = [
    "AGENTS.md",
    "README.md",
    "ETHOS.md",
    ".codex/config.toml",
    ".codex/hooks.json",
    "harness/runtime.json",
    "harness/model_policy.json",
    "templates/Plan.md",
    "templates/Review.md",
    ".github/workflows/harness.yml",
    "docs/ai/operations.md",
    "scripts/harness/gate.py",
    "scripts/harness/bootstrap.py",
    "scripts/harness/review_gate.py",
    "scripts/harness/subagent_planner.py",
    "scripts/harness/automation_planner.py",
    "scripts/harness/skillify_audit.py",
    "scripts/harness/adopt_project.py",
    "scripts/harness/score.py",
    "scripts/harness/session_close.py",
]

FORBIDDEN_MUTABLE_CODEX = [
    ".codex/runtime.json",
    ".codex/context",
    ".codex/reviews",
    ".codex/telemetry",
    ".codex/audits",
]


def read_toml(path: Path) -> dict:
    """Parse the small TOML subset used by this template.

    This avoids requiring Python 3.11's tomllib so the harness works with the
    default macOS Python 3.9 runtime.
    """
    data: dict = {}
    current: dict = data
    in_multiline = False
    multiline_key = ""
    buffer: list[str] = []

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if in_multiline:
            if line.endswith('"""'):
                buffer.append(raw_line.rsplit('"""', 1)[0])
                current[multiline_key] = "\n".join(buffer)
                in_multiline = False
                multiline_key = ""
                buffer = []
            else:
                buffer.append(raw_line)
            continue
        if line.startswith("[") and line.endswith("]"):
            section = line.strip("[]")
            current = data
            for part in section.split("."):
                current = current.setdefault(part, {})
            continue
        if "=" not in line:
            continue
        key, value = [part.strip() for part in line.split("=", 1)]
        if value == '"""':
            in_multiline = True
            multiline_key = key
            buffer = []
        elif value.startswith('"') and value.endswith('"'):
            current[key] = value.strip('"')
        elif value in {"true", "false"}:
            current[key] = value == "true"
        else:
            try:
                current[key] = int(value)
            except ValueError:
                current[key] = value
    return data


def skill_metadata(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
    if not match:
        return {}
    metadata = {}
    for line in match.group(1).splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            metadata[key.strip()] = value.strip().strip('"')
    return metadata


def main() -> int:
    errors: list[str] = []

    for rel in REQUIRED_FILES:
        if not (ROOT / rel).exists():
            errors.append(f"missing required file: {rel}")

    for rel in FORBIDDEN_MUTABLE_CODEX:
        if (ROOT / rel).exists():
            errors.append(f"mutable state must not live under .codex: {rel}")

    try:
        config = read_toml(ROOT / ".codex/config.toml")
        agents = config.get("agents", {})
        if agents.get("max_depth") != 1:
            errors.append(".codex/config.toml should set agents.max_depth = 1")
        if agents.get("max_threads", 0) < 2:
            errors.append(".codex/config.toml should allow at least 2 agent threads")
    except Exception as exc:
        errors.append(f"invalid .codex/config.toml: {exc}")

    try:
        runtime = json.loads((ROOT / "harness/runtime.json").read_text(encoding="utf-8"))
        if runtime.get("deployment_profile") not in {"template", "project"}:
            errors.append("runtime deployment_profile must be template or project")
        if runtime.get("state_root") != "harness":
            errors.append("runtime state_root must be harness")
    except Exception as exc:
        errors.append(f"invalid harness/runtime.json: {exc}")

    try:
        model_policy = json.loads((ROOT / "harness/model_policy.json").read_text(encoding="utf-8"))
        if model_policy.get("frontier_model") != "gpt-5.5":
            errors.append("model_policy frontier_model must be gpt-5.5")
    except Exception as exc:
        errors.append(f"invalid harness/model_policy.json: {exc}")

    agent_files = sorted((ROOT / ".codex/agents").glob("*.toml"))
    if len(agent_files) < 6:
        errors.append("expected at least 6 custom agent files")
    for path in agent_files:
        try:
            data = read_toml(path)
        except Exception as exc:
            errors.append(f"invalid agent TOML {path.relative_to(ROOT)}: {exc}")
            continue
        for key in ["name", "description", "developer_instructions"]:
            if not data.get(key):
                errors.append(f"agent {path.name} missing {key}")
        if data.get("name") != "browser_debugger" and data.get("sandbox_mode") != "read-only":
            errors.append(f"agent {path.name} should be read-only")

    skill_files = sorted((ROOT / ".agents/skills").glob("*/SKILL.md"))
    if len(skill_files) < 5:
        errors.append("expected at least 5 repo skills")
    seen_names: set[str] = set()
    for path in skill_files:
        meta = skill_metadata(path)
        if not meta.get("name") or not meta.get("description"):
            errors.append(f"skill missing name/description: {path.relative_to(ROOT)}")
        if meta.get("name") in seen_names:
            errors.append(f"duplicate skill name: {meta.get('name')}")
        seen_names.add(meta.get("name", ""))

    for command in [
        [sys.executable, "scripts/harness/gate.py", "all", "--tier", "trivial", "--json"],
        [sys.executable, "scripts/harness/gate.py", "all", "--tier", "normal", "--template", "--json"],
        [sys.executable, "scripts/harness/subagent_planner.py", "check", "--quiet"],
        [sys.executable, "scripts/harness/automation_planner.py", "audit"],
        [sys.executable, "scripts/harness/skillify_audit.py", "all", "--json"],
        [sys.executable, "scripts/harness/adopt_project.py", "--check"],
        [sys.executable, "scripts/harness/session_close.py", "--tier", "high-risk", "--template", "--json"],
    ]:
        proc = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)
        if proc.returncode != 0:
            errors.append(f"gate command failed: {' '.join(command)}\n{proc.stdout}\n{proc.stderr}")

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print("self-test ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
