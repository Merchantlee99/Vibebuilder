#!/usr/bin/env python3
"""Install the GPT-5.6 native-first router into a user's Codex globals."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]

GLOBAL_BLOCK = """<!-- VIBEBUILDER:CODEX-5-6:BEGIN -->
## GPT-5.6 personal defaults

- Lead with the outcome and include only the evidence needed for material claims.
- Treat answer, explain, review, diagnose, analyze, and plan requests as read-only unless the user also asks for a change.
- For build, change, or fix requests, make only the requested local changes and run relevant non-destructive checks.
- Require explicit user intent for remote writes, deployment, destructive actions, purchases, secrets, or material scope expansion.
- Let GPT-5.6 handle ordinary decomposition natively. Load a specialized skill only when its trigger matches; do not route every complex task through a meta-router.
- Keep repo commands and conventions in the nearest repo AGENTS.md.
- Use Lazyweb for substantial product-UI discovery, critique, or redesign; skip it for scoped fixes or faithful implementation from an existing design, then use visual QA after UI changes.
<!-- VIBEBUILDER:CODEX-5-6:END -->
"""

MANAGED_BLOCK_PATTERNS = [
    re.compile(r"<!-- LAZYWEB:ROUTER:BEGIN.*?<!-- LAZYWEB:ROUTER:END -->\s*", re.DOTALL),
    re.compile(
        r"<!-- CODEX-EXTREME-OPERATOR:BEGIN.*?<!-- CODEX-EXTREME-OPERATOR:END -->\s*",
        re.DOTALL,
    ),
    re.compile(r"<!-- VIBEBUILDER:CODEX-5-6:BEGIN.*?<!-- VIBEBUILDER:CODEX-5-6:END -->\s*", re.DOTALL),
]


def default_codex_home() -> Path:
    return Path(os.environ.get("CODEX_HOME", "~/.codex")).expanduser()


def update_agents_text(text: str) -> str:
    preserved = text
    for pattern in MANAGED_BLOCK_PATTERNS:
        preserved = pattern.sub("", preserved)
    preserved = preserved.strip()
    if preserved:
        return f"{GLOBAL_BLOCK}\n{preserved}\n"
    return GLOBAL_BLOCK


def remove_managed_skill_blocks(text: str, managed_paths: set[str]) -> str:
    lines = text.splitlines(keepends=True)
    output: list[str] = []
    index = 0
    while index < len(lines):
        if lines[index].strip() != "[[skills.config]]":
            output.append(lines[index])
            index += 1
            continue

        end = index + 1
        while end < len(lines) and not lines[end].lstrip().startswith("["):
            end += 1
        block = "".join(lines[index:end])
        path_match = re.search(r'^path\s*=\s*"([^"]+)"', block, flags=re.MULTILINE)
        if not path_match or path_match.group(1) not in managed_paths:
            output.append(block)
        index = end
    return "".join(output)


def migrate_legacy_config(text: str) -> tuple[str, list[str]]:
    lines = text.splitlines(keepends=True)
    section = ""
    features_hooks_present = False
    legacy_hooks_enabled = False

    for line in lines:
        header = re.match(r"^\s*\[([^\[][^\]]*)\]\s*$", line)
        if header:
            section = header.group(1)
            continue
        key_match = re.match(r"^\s*([A-Za-z0-9_-]+)\s*=\s*(.*?)\s*$", line)
        if section == "features" and key_match:
            key, value = key_match.groups()
            if key == "hooks":
                features_hooks_present = True
            if key in {"plugin_hooks", "codex_hooks"} and value.lower() == "true":
                legacy_hooks_enabled = True

    output: list[str] = []
    removed: list[str] = []
    section = ""
    inserted_hooks = False
    for line in lines:
        header = re.match(r"^\s*\[([^\[][^\]]*)\]\s*$", line)
        if header:
            section = header.group(1)
            output.append(line)
            continue
        key_match = re.match(r"^\s*([A-Za-z0-9_-]+)\s*=", line)
        key = key_match.group(1) if key_match else None
        if section == "" and key == "network_access":
            removed.append("network_access")
            continue
        if section == "features" and key == "child_agents_md":
            removed.append("features.child_agents_md")
            continue
        if section == "features" and key in {"plugin_hooks", "codex_hooks"}:
            removed.append(f"features.{key}")
            if not features_hooks_present and not inserted_hooks:
                output.append(f"hooks = {'true' if legacy_hooks_enabled else 'false'}\n")
                inserted_hooks = True
            continue
        output.append(line)
    return "".join(output), removed


def update_config_text(
    text: str, *, effort: str, skill_states: list[tuple[Path, bool]]
) -> tuple[str, list[str]]:
    migrated, removed_legacy_config_keys = migrate_legacy_config(text)
    effort_line = f'model_reasoning_effort = "{effort}"'
    if re.search(r"^model_reasoning_effort\s*=.*$", migrated, flags=re.MULTILINE):
        updated = re.sub(r"^model_reasoning_effort\s*=.*$", effort_line, migrated, flags=re.MULTILINE)
    elif re.search(r"^model\s*=.*$", migrated, flags=re.MULTILINE):
        updated = re.sub(r"^(model\s*=.*)$", rf"\1\n{effort_line}", migrated, count=1, flags=re.MULTILINE)
    else:
        updated = f"{effort_line}\n{migrated}"

    managed_paths = {str(path) for path, _ in skill_states}
    updated = remove_managed_skill_blocks(updated, managed_paths).rstrip()
    blocks = []
    for path, enabled in skill_states:
        blocks.append(
            "\n".join(
                [
                    "[[skills.config]]",
                    f"path = {json.dumps(str(path))}",
                    f"enabled = {'true' if enabled else 'false'}",
                ]
            )
        )
    rendered_blocks = "\n\n".join(blocks)
    return f"{updated}\n\n{rendered_blocks}\n", removed_legacy_config_keys


def copy_skill(source: Path, destination: Path) -> None:
    staging = destination.parent / f".{destination.name}.tmp-{os.getpid()}"
    if staging.exists():
        shutil.rmtree(staging)
    shutil.copytree(
        source,
        staging,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store", ".git"),
    )
    if destination.exists():
        shutil.rmtree(destination)
    staging.replace(destination)


def create_backup(backup_root: Path, paths: list[tuple[Path, str]]) -> None:
    backup_root.mkdir(parents=True, exist_ok=False)
    for source, relative_name in paths:
        if not source.exists():
            continue
        destination = backup_root / relative_name
        destination.parent.mkdir(parents=True, exist_ok=True)
        if source.is_dir():
            shutil.copytree(source, destination)
        else:
            shutil.copy2(source, destination)


def remove_active_path(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.exists():
        shutil.rmtree(path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--codex-home", type=Path, default=default_codex_home())
    parser.add_argument("--agents-home", type=Path, default=Path("~/.agents").expanduser())
    parser.add_argument("--effort", choices=["minimal", "low", "medium", "high", "xhigh"], default="high")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    codex_home = args.codex_home.expanduser().resolve()
    agents_home = args.agents_home.expanduser().resolve()
    agents_path = codex_home / "AGENTS.md"
    config_path = codex_home / "config.toml"
    install_path = agents_home / "skills" / "codex-skill-router"

    skill_states = [
        (codex_home / "skills" / "codex-extreme-operator", False),
        (codex_home / "skills" / "design-impact-router", False),
        (agents_home / "skills" / "apex", False),
        (install_path, True),
    ]
    legacy_skill_paths = [path for path, enabled in skill_states if not enabled]
    archived_legacy_skills = [path for path in legacy_skill_paths if path.exists() or path.is_symlink()]

    existing_agents = agents_path.read_text(encoding="utf-8") if agents_path.exists() else ""
    existing_config = config_path.read_text(encoding="utf-8") if config_path.exists() else ""
    next_agents = update_agents_text(existing_agents)
    next_config, removed_legacy_config_keys = update_config_text(
        existing_config, effort=args.effort, skill_states=skill_states
    )
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    backup_root = codex_home / "backups" / "vibebuilder-codex-5-6" / timestamp

    report = {
        "dry_run": args.dry_run,
        "effort": args.effort,
        "installed_skill": str(install_path),
        "agents_file": str(agents_path),
        "config_file": str(config_path),
        "backup": str(backup_root),
        "agents_changed": existing_agents != next_agents,
        "config_changed": existing_config != next_config,
        "disabled_legacy_skills": [str(path) for path, enabled in skill_states if not enabled],
        "archived_legacy_skills": [str(path) for path in archived_legacy_skills],
        "removed_legacy_config_keys": removed_legacy_config_keys,
    }

    if args.dry_run:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    create_backup(
        backup_root,
        [
            (agents_path, "AGENTS.md"),
            (config_path, "config.toml"),
            (install_path, "codex-skill-router"),
            *[(path, f"legacy-skills/{path.name}") for path in archived_legacy_skills],
        ],
    )
    agents_path.parent.mkdir(parents=True, exist_ok=True)
    install_path.parent.mkdir(parents=True, exist_ok=True)
    agents_path.write_text(next_agents, encoding="utf-8")
    config_path.write_text(next_config, encoding="utf-8")
    for legacy_path in archived_legacy_skills:
        remove_active_path(legacy_path)
    copy_skill(SKILL_ROOT, install_path)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
