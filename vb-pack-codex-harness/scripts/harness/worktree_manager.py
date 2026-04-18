#!/usr/bin/env python3
"""Helpers for git worktree flows in Codex-native projects."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


def repo_root() -> Path | None:
    current = Path.cwd().resolve()
    for candidate in (current, *current.parents):
        if (candidate / ".git").exists():
            return candidate
    return None


def run_git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=str(root),
        capture_output=True,
        text=True,
        check=False,
    )


def default_worktree_path(root: Path, name: str) -> Path:
    return root.parent / f"{root.name}__wt__{name}"


def has_head_commit(root: Path) -> bool:
    proc = run_git(root, "rev-parse", "--verify", "HEAD")
    return proc.returncode == 0


def init_repo(root: Path, branch: str, seed_empty_commit: bool) -> int:
    if (root / ".git").exists():
        print("git repository already initialized")
        return 0

    proc = subprocess.run(
        ["git", "init", "-b", branch],
        cwd=str(root),
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        fallback = subprocess.run(
            ["git", "init"],
            cwd=str(root),
            capture_output=True,
            text=True,
            check=False,
        )
        if fallback.returncode != 0:
            print(fallback.stderr.strip() or fallback.stdout.strip() or proc.stderr.strip(), file=sys.stderr)
            return fallback.returncode or 1
        subprocess.run(
            ["git", "checkout", "-B", branch],
            cwd=str(root),
            capture_output=True,
            text=True,
            check=False,
        )

    if not seed_empty_commit:
        print(f"initialized git repository on {branch}")
        return 0

    commit_env = dict(os.environ)
    commit_env.setdefault("GIT_AUTHOR_NAME", "Codex Harness")
    commit_env.setdefault("GIT_AUTHOR_EMAIL", "codex-harness@local")
    commit_env.setdefault("GIT_COMMITTER_NAME", commit_env["GIT_AUTHOR_NAME"])
    commit_env.setdefault("GIT_COMMITTER_EMAIL", commit_env["GIT_AUTHOR_EMAIL"])
    commit = subprocess.run(
        ["git", "commit", "--allow-empty", "-m", "chore: initialize codex harness"],
        cwd=str(root),
        capture_output=True,
        text=True,
        check=False,
        env=commit_env,
    )
    if commit.returncode != 0:
        print(commit.stderr.strip() or commit.stdout.strip(), file=sys.stderr)
        return commit.returncode
    print(f"initialized git repository on {branch} with empty commit")
    return 0


def create_worktree(root: Path, name: str, base: str, path_arg: str | None) -> int:
    path = Path(path_arg).expanduser().resolve() if path_arg else default_worktree_path(root, name)
    branch = f"wt/{name}"
    if path.exists():
        print(f"path already exists: {path}", file=sys.stderr)
        return 1
    if not has_head_commit(root):
        print("cannot create worktree before the repository has at least one commit", file=sys.stderr)
        return 1
    proc = run_git(root, "worktree", "add", str(path), "-b", branch, base)
    if proc.returncode != 0:
        print(proc.stderr.strip() or proc.stdout.strip(), file=sys.stderr)
        return proc.returncode
    print(path)
    return 0


def list_worktrees(root: Path) -> int:
    proc = run_git(root, "worktree", "list")
    if proc.returncode != 0:
        print(proc.stderr.strip() or proc.stdout.strip(), file=sys.stderr)
        return proc.returncode
    print(proc.stdout.strip())
    return 0


def remove_worktree(root: Path, path: str) -> int:
    proc = run_git(root, "worktree", "remove", path)
    if proc.returncode != 0:
        print(proc.stderr.strip() or proc.stdout.strip(), file=sys.stderr)
        return proc.returncode
    print("ok")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)

    init_repo_cmd = sub.add_parser("init-repo")
    init_repo_cmd.add_argument("--branch", default="main")
    init_repo_cmd.add_argument("--seed-empty-commit", action="store_true")

    create = sub.add_parser("create")
    create.add_argument("name")
    create.add_argument("--base", default="HEAD")
    create.add_argument("--path", default=None)

    sub.add_parser("list")

    remove = sub.add_parser("remove")
    remove.add_argument("path")

    args = parser.parse_args()
    if args.cmd == "init-repo":
        return init_repo(Path.cwd().resolve(), args.branch, args.seed_empty_commit)

    root = repo_root()
    if root is None:
        print("git repository not initialized", file=sys.stderr)
        return 1

    if args.cmd == "create":
        return create_worktree(root, args.name, args.base, args.path)
    if args.cmd == "list":
        return list_worktrees(root)
    return remove_worktree(root, args.path)


if __name__ == "__main__":
    raise SystemExit(main())
