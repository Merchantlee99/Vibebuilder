#!/usr/bin/env python3
"""Summarize current git changes for review preparation."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


HIGH_RISK_KEYWORDS = ("auth", "payment", "billing", "security", "migration", "infra")


def repo_root() -> Path:
    proc = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=str(Path.cwd()),
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError("git repository not initialized")
    return Path(proc.stdout.strip()).resolve()


def git(*args: str) -> str:
    proc = subprocess.run(
        ["git", *args],
        cwd=str(repo_root()),
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or "git command failed")
    return proc.stdout.strip()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="HEAD")
    args = parser.parse_args()

    try:
        repo_root()
        files = [line for line in git("diff", "--name-only", args.base).splitlines() if line]
        stat = git("diff", "--stat", args.base)
    except RuntimeError as exc:
        print(f"# Review Digest\n\n- {exc}")
        return 0

    print("# Review Digest")
    print()
    print(f"- changed files: {len(files)}")
    for file_path in files:
        tag = " high-risk" if any(keyword in file_path.lower() for keyword in HIGH_RISK_KEYWORDS) else ""
        print(f"- {file_path}{tag}")
    if stat:
        print()
        print("## Diff Stat")
        print(stat)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
