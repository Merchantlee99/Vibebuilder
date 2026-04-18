#!/usr/bin/env python3
"""Protect control-plane files from casual edits."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


PROTECTED_PATTERNS = [
    r"^AGENTS\.md$",
    r"^ETHOS\.md$",
    r"^\.codex/runtime\.json$",
    r"^\.codex/hooks\.json$",
    r"^\.codex/hooks/",
    r"^\.codex/manifests/",
    r"^\.codex/telemetry/",
    r"^\.codex/context/activity-state\.json$",
    r"^\.codex/context/session\.json$",
    r"^\.codex/context/ownership\.json$",
    r"^\.codex/context/subagent-tasks\.json$",
    r"^\.codex/context/automation-intents\.json$",
    r"^scripts/harness/",
]


def repo_root() -> Path:
    current = Path.cwd().resolve()
    for candidate in (current, *current.parents):
        if (candidate / ".codex").exists() or (candidate / ".git").exists():
            return candidate
    return current


def runtime_mode(root: Path) -> str:
    try:
        return json.loads((root / ".codex" / "runtime.json").read_text(encoding="utf-8")).get("mode", "advisory")
    except Exception:
        return "advisory"


def normalize(root: Path, raw: str) -> str:
    path = raw.replace("\\", "/")
    if Path(path).is_absolute():
        try:
            path = str(Path(path).resolve().relative_to(root.resolve())).replace("\\", "/")
        except Exception:
            pass
    while path.startswith("./"):
        path = path[2:]
    return path


def violations_for_paths(root: Path, paths: list[str], allow_control_plane: bool, allow_telemetry: bool) -> list[str]:
    if allow_control_plane:
        return []
    violations: list[str] = []
    for raw in paths:
        rel = normalize(root, raw)
        matched = None
        for pattern in PROTECTED_PATTERNS:
            if re.search(pattern, rel):
                matched = pattern
                break
        if matched is None:
            continue
        if allow_telemetry and rel.startswith(".codex/telemetry/"):
            continue
        violations.append(f"protected path blocked: {rel} (pattern: {matched})")
    return violations


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--allow-control-plane", action="store_true")
    parser.add_argument("--allow-telemetry", action="store_true")
    parser.add_argument("paths", nargs="+")
    args = parser.parse_args()

    root = repo_root()
    violations = violations_for_paths(root, args.paths, args.allow_control_plane, args.allow_telemetry)
    mode = runtime_mode(root)
    if not violations:
        print("ok")
        return 0
    label = "BLOCKED" if mode == "enforced" else "ADVISORY"
    print(label)
    for violation in violations:
        print(f"- {violation}")
    return 2 if mode == "enforced" else 0


if __name__ == "__main__":
    raise SystemExit(main())
