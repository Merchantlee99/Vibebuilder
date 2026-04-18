#!/usr/bin/env python3
"""
gate_4_runner.py — Detached deterministic-tool runner for Gate ④.

Invoked by post_tool_use.py in a new session (not blocking the editor).
Detects project toolchain, runs available linters + type checkers + test
suite, captures tail output, and records outcome to events.jsonl.

Argv:
  [1] repo_root
  [2] target_file (the file the user just edited)

Outcome rules:
  - If no toolchain detected → outcome="skip" with reason="no-toolchain"
  - If any tool exits non-zero → outcome="block"
  - If all tools pass → outcome="pass"

Output tail saved to .claude/test-runs/run-<ts>.log.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path


def _run_tool(name: str, argv: list[str], cwd: Path, log_fh, timeout: int = 120) -> tuple[str, int]:
    """Run a tool, stream output to log_fh, return (name, exit_code).

    Tools that miss their binary return exit code 127.
    """
    log_fh.write(f"\n=== {name}: {' '.join(argv)} ===\n")
    log_fh.flush()
    try:
        r = subprocess.run(
            argv, cwd=str(cwd), stdout=log_fh, stderr=subprocess.STDOUT,
            timeout=timeout, text=False,
        )
        return name, r.returncode
    except FileNotFoundError:
        log_fh.write(f"(missing: {argv[0]})\n")
        return name, 127
    except subprocess.TimeoutExpired:
        log_fh.write(f"(timeout after {timeout}s)\n")
        return name, 124
    except Exception as exc:
        log_fh.write(f"(error: {exc})\n")
        return name, 1


def _has_binary(name: str) -> bool:
    from shutil import which
    return which(name) is not None


def main() -> int:
    if len(sys.argv) < 3:
        return 2
    repo_root = Path(sys.argv[1]).resolve()
    target_file = sys.argv[2]

    # Set up log file
    runs_dir = repo_root / ".claude" / "test-runs"
    runs_dir.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    log_file = runs_dir / f"run-{stamp}.log"

    results: list[tuple[str, int]] = []

    with open(log_file, "wb") as lf:
        # Detect Python project
        is_py = (repo_root / "pyproject.toml").exists()
        if not is_py:
            # also if any top-level .py
            for p in repo_root.iterdir():
                if p.is_file() and p.suffix == ".py":
                    is_py = True
                    break

        if is_py:
            if _has_binary("ruff"):
                results.append(_run_tool("ruff", ["ruff", "check", "."], repo_root, lf))
            if _has_binary("mypy") and (repo_root / "pyproject.toml").exists():
                results.append(_run_tool(
                    "mypy", ["mypy", "--ignore-missing-imports", "."], repo_root, lf))
            tests_dir = repo_root / "tests"
            if tests_dir.exists():
                if _has_binary("pytest"):
                    results.append(_run_tool(
                        "pytest", ["pytest", "-q", "--no-header"], repo_root, lf))
                else:
                    results.append(_run_tool(
                        "unittest", ["python3", "-m", "unittest", "discover",
                                     "-s", "tests", "-q"], repo_root, lf))

        # Detect Node project
        pkg = repo_root / "package.json"
        if pkg.exists() and _has_binary("npm"):
            try:
                pkg_data = json.loads(pkg.read_text(encoding="utf-8"))
                scripts = pkg_data.get("scripts", {}) or {}
                if "lint" in scripts:
                    results.append(_run_tool(
                        "npm-lint", ["npm", "run", "--silent", "lint"], repo_root, lf))
                if "typecheck" in scripts:
                    results.append(_run_tool(
                        "npm-typecheck",
                        ["npm", "run", "--silent", "typecheck"], repo_root, lf))
                if "test" in scripts:
                    results.append(_run_tool(
                        "npm-test",
                        ["npm", "test", "--silent"], repo_root, lf))
            except Exception:
                pass

        # Detect Go project
        if (repo_root / "go.mod").exists() and _has_binary("go"):
            results.append(_run_tool("go-vet", ["go", "vet", "./..."], repo_root, lf))
            results.append(_run_tool("go-test", ["go", "test", "./..."], repo_root, lf))

    # Compute outcome + summary
    commit_hash = ""
    try:
        commit_hash = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=str(repo_root), text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except Exception:
        commit_hash = "no-git"

    if not results:
        outcome = "skip"
        reason = "no-toolchain"
    else:
        failed = [n for n, code in results if code not in (0,)]
        if failed:
            outcome = "block"
            reason = f"tools failed: {failed}"
        else:
            outcome = "pass"
            reason = "all tools green"

    tools_ran = [n for n, _ in results]
    tools_pass = [n for n, code in results if code == 0]
    tools_fail = [n for n, code in results if code not in (0,)]

    # Record event
    sys.path.insert(0, str(repo_root / "scripts" / "harness"))
    try:
        import event_log  # type: ignore
        event_log.append_event(
            gate="04", outcome=outcome, actor="system",
            file_path=target_file,
            detail={
                "commit": commit_hash,
                "log": str(log_file),
                "tools_ran": tools_ran,
                "tools_pass": tools_pass,
                "tools_fail": tools_fail,
                "reason": reason,
            },
            repo_root=repo_root,
        )
    except Exception:
        pass

    return 0


if __name__ == "__main__":
    sys.exit(main())
