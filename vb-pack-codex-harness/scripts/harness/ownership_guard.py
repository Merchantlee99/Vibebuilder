#!/usr/bin/env python3
"""Track and enforce write-path ownership for parallel Codex work."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import PurePosixPath, Path


STATE_PATH = Path(".codex/context/ownership.json")


def repo_root() -> Path:
    current = Path.cwd().resolve()
    for candidate in (current, *current.parents):
        if (candidate / ".codex").exists() or (candidate / ".git").exists():
            return candidate
    return current


def state_path(root: Path) -> Path:
    return root / STATE_PATH


def load_state(root: Path) -> dict:
    path = state_path(root)
    if not path.exists():
        return {"claims": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        data = {"claims": {}}
    if "claims" not in data or not isinstance(data["claims"], dict):
        data = {"claims": {}}
    return data


def save_state(root: Path, state: dict) -> None:
    path = state_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


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
    return path.rstrip("/")


def overlaps(left: str, right: str) -> bool:
    a = PurePosixPath(left)
    b = PurePosixPath(right)
    a_parts = a.parts
    b_parts = b.parts
    shorter = a_parts if len(a_parts) <= len(b_parts) else b_parts
    longer = b_parts if shorter is a_parts else a_parts
    return tuple(longer[: len(shorter)]) == tuple(shorter)


def conflict_messages(root: Path, owner: str, paths: list[str]) -> list[str]:
    state = load_state(root)
    claims = state.get("claims", {})
    messages: list[str] = []
    for other_owner, payload in claims.items():
        if other_owner == owner:
            continue
        other_paths = payload.get("paths", [])
        for path in paths:
            for other_path in other_paths:
                if overlaps(path, other_path):
                    messages.append(f"path conflict: {path} overlaps {other_path} owned by {other_owner}")
    return messages


def claim_paths(root: Path, owner: str, paths: list[str], mode: str) -> int:
    normalized = [normalize(root, path) for path in paths]
    conflicts = conflict_messages(root, owner, normalized)
    run_mode = runtime_mode(root)
    if conflicts:
        label = "BLOCKED" if run_mode == "enforced" else "ADVISORY"
        print(label)
        for conflict in conflicts:
            print(f"- {conflict}")
        if run_mode == "enforced":
            return 2

    state = load_state(root)
    state["claims"][owner] = {
        "paths": sorted(set(normalized)),
        "mode": mode,
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    save_state(root, state)
    print("ok")
    return 0


def release_owner(root: Path, owner: str) -> int:
    state = load_state(root)
    state.get("claims", {}).pop(owner, None)
    save_state(root, state)
    print("ok")
    return 0


def show_status(root: Path) -> int:
    print(json.dumps(load_state(root), indent=2, ensure_ascii=False))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)

    claim = sub.add_parser("claim")
    claim.add_argument("--owner", required=True)
    claim.add_argument("--mode", default="worktree")
    claim.add_argument("paths", nargs="+")

    release = sub.add_parser("release")
    release.add_argument("--owner", required=True)

    check = sub.add_parser("check")
    check.add_argument("--owner", required=True)
    check.add_argument("paths", nargs="+")

    sub.add_parser("status")

    args = parser.parse_args()
    root = repo_root()

    if args.cmd == "claim":
        return claim_paths(root, args.owner, args.paths, args.mode)
    if args.cmd == "release":
        return release_owner(root, args.owner)
    if args.cmd == "check":
        conflicts = conflict_messages(root, args.owner, [normalize(root, path) for path in args.paths])
        if not conflicts:
            print("ok")
            return 0
        label = "BLOCKED" if runtime_mode(root) == "enforced" else "ADVISORY"
        print(label)
        for conflict in conflicts:
            print(f"- {conflict}")
        return 2 if runtime_mode(root) == "enforced" else 0
    return show_status(root)


if __name__ == "__main__":
    raise SystemExit(main())
