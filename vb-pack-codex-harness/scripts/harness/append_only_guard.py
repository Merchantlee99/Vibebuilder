#!/usr/bin/env python3
"""Verify that a candidate file only appends to an existing file."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


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


def check_append_only(existing: Path, candidate: Path) -> list[str]:
    violations: list[str] = []
    if not candidate.exists():
        return [f"candidate file missing: {candidate}"]
    if not existing.exists():
        return []
    old = existing.read_bytes()
    new = candidate.read_bytes()
    if not new.startswith(old):
        violations.append("candidate content is not an append-only extension of the existing file")
    return violations


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--existing", required=True)
    parser.add_argument("--candidate", required=True)
    args = parser.parse_args()

    root = repo_root()
    violations = check_append_only(root / args.existing, root / args.candidate)
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
