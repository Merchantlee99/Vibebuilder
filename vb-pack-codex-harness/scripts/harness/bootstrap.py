#!/usr/bin/env python3
"""Ensure the Codex-native harness runtime directories and logs exist."""

from __future__ import annotations

import argparse
import ast
import json
import os
import stat
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]

REQUIRED_DIRS = [
    ".codex/context",
    ".codex/hooks",
    ".codex/telemetry",
    ".codex/manifests",
    ".codex/reviews",
    ".codex/audits",
    ".codex/playbooks",
    ".codex/skills/_proposed",
    "templates",
    "scripts/harness",
    "tests",
]

LOG_FILES = [
    ".codex/telemetry/events.jsonl",
    ".codex/telemetry/learnings.jsonl",
]

CONTROL_FILES = {
    ".codex/context/ownership.json": '{\n  "claims": {}\n}\n',
    ".codex/context/activity-state.json": '{\n  "files": {}\n}\n',
    ".codex/context/subagent-tasks.json": '{\n  "tasks": {}\n}\n',
    ".codex/context/automation-intents.json": '{\n  "generated_at": "",\n  "suggestions": []\n}\n',
}

PROJECT_DEFAULT_FOCUS = "use the codex harness on this copied project and validate the first real delivery loop"


def ensure_dirs() -> tuple[bool, str]:
    created = 0
    for rel in REQUIRED_DIRS:
        path = REPO_ROOT / rel
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
            created += 1
    return True, f"{created} directories created"


def ensure_logs(reset: bool) -> tuple[bool, str]:
    touched = 0
    for rel in LOG_FILES:
        path = REPO_ROOT / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        if reset or not path.exists():
            path.write_text("", encoding="utf-8")
            touched += 1
    return True, f"{touched} log files initialized"


def ensure_control_files() -> tuple[bool, str]:
    touched = 0
    for rel, content in CONTROL_FILES.items():
        path = REPO_ROOT / rel
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            touched += 1
    return True, f"{touched} control files initialized"


def ensure_executable() -> tuple[bool, str]:
    count = 0
    for directory in (REPO_ROOT / "scripts" / "harness", REPO_ROOT / ".codex" / "hooks"):
        if not directory.exists():
            continue
        for path in directory.glob("*.py"):
            mode = path.stat().st_mode
            path.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
            count += 1
    return True, f"{count} scripts marked executable"


def validate_runtime() -> tuple[bool, str]:
    runtime_path = REPO_ROOT / ".codex" / "runtime.json"
    if not runtime_path.exists():
        return False, "missing .codex/runtime.json"
    try:
        json.loads(runtime_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return False, f"invalid runtime.json: {exc}"
    return True, "runtime.json valid"


def adopt_project_runtime(project_focus: str | None) -> tuple[bool, str]:
    runtime_path = REPO_ROOT / ".codex" / "runtime.json"
    if not runtime_path.exists():
        return False, "missing .codex/runtime.json"
    runtime = json.loads(runtime_path.read_text(encoding="utf-8"))
    runtime["deployment_profile"] = "project"
    runtime["mode"] = "advisory"
    runtime["stage"] = "project-bootstrap"
    runtime["current_focus"] = (project_focus or PROJECT_DEFAULT_FOCUS).strip()
    hook_adapter = runtime.get("hook_adapter", {})
    if not isinstance(hook_adapter, dict):
        hook_adapter = {}
    hook_adapter["enabled"] = True
    runtime["hook_adapter"] = hook_adapter
    runtime_path.write_text(json.dumps(runtime, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return True, "runtime adopted as project instance"


def ensure_git_repo(init_git: bool, branch: str, seed_empty_commit: bool) -> tuple[bool, str]:
    git_dir = REPO_ROOT / ".git"
    if git_dir.exists():
        return True, "git repo ready"
    if not init_git:
        return True, "git repo not initialized (skipped)"

    proc = subprocess.run(
        ["git", "init", "-b", branch],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        fallback = subprocess.run(
            ["git", "init"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            check=False,
        )
        if fallback.returncode != 0:
            message = fallback.stderr.strip() or fallback.stdout.strip() or proc.stderr.strip() or "git init failed"
            return False, message
        subprocess.run(
            ["git", "checkout", "-B", branch],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            check=False,
        )

    if not seed_empty_commit:
        return True, f"git repo initialized on {branch}"

    commit_env = dict(os.environ)
    commit_env.setdefault("GIT_AUTHOR_NAME", "Codex Harness")
    commit_env.setdefault("GIT_AUTHOR_EMAIL", "codex-harness@local")
    commit_env.setdefault("GIT_COMMITTER_NAME", commit_env["GIT_AUTHOR_NAME"])
    commit_env.setdefault("GIT_COMMITTER_EMAIL", commit_env["GIT_AUTHOR_EMAIL"])
    commit = subprocess.run(
        ["git", "commit", "--allow-empty", "-m", "chore: initialize codex harness"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
        env=commit_env,
    )
    if commit.returncode != 0:
        message = commit.stderr.strip() or commit.stdout.strip() or "empty commit failed"
        return False, message
    return True, f"git repo initialized on {branch} with empty commit"


def syntax_check_scripts() -> tuple[bool, str]:
    checked = 0
    for path in (REPO_ROOT / "scripts" / "harness").glob("*.py"):
        ast.parse(path.read_text(encoding="utf-8"))
        checked += 1
    return True, f"{checked} scripts parsed"


def run_self_test() -> tuple[bool, str]:
    proc = subprocess.run(
        ["python3", str(REPO_ROOT / "scripts" / "harness" / "self_test.py")],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        tail = "\n".join((proc.stdout + proc.stderr).splitlines()[-10:])
        return False, f"self-test failed\n{tail}"
    return True, "self-test passed"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset-logs", action="store_true")
    parser.add_argument("--skip-self-test", action="store_true")
    parser.add_argument("--init-git", action="store_true")
    parser.add_argument("--seed-empty-commit", action="store_true")
    parser.add_argument("--git-branch", default="main")
    parser.add_argument("--adopt-project", action="store_true")
    parser.add_argument("--project-focus", default="")
    args = parser.parse_args()

    steps = [
        ("dirs", ensure_dirs),
        ("logs", lambda: ensure_logs(args.reset_logs)),
        ("control-files", ensure_control_files),
        ("git", lambda: ensure_git_repo(args.init_git, args.git_branch, args.seed_empty_commit)),
        ("deployment-profile", lambda: adopt_project_runtime(args.project_focus) if args.adopt_project else (True, "template profile preserved")),
        ("chmod", ensure_executable),
        ("runtime", validate_runtime),
        ("syntax", syntax_check_scripts),
    ]
    if not args.skip_self_test:
        steps.append(("self-test", run_self_test))

    failed = False
    for label, fn in steps:
        try:
            ok, message = fn()
        except Exception as exc:  # pragma: no cover - defensive bootstrap behavior
            ok, message = False, str(exc)
        mark = "ok" if ok else "FAIL"
        print(f"[{mark}] {label}: {message}")
        failed = failed or not ok
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
