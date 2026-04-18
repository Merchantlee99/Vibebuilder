#!/usr/bin/env python3
"""Infer append-only telemetry events from tracked harness artifact changes."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import event_log
else:  # pragma: no cover - package import path
    from . import event_log


STATE_FILE = Path(".codex/context/activity-state.json")

TRACKED_FILES = {
    "AGENTS.md": ("harness-doc", "governance"),
    "README.md": ("harness-doc", "governance"),
    "ETHOS.md": ("harness-doc", "governance"),
    "Prompt.md": ("planning-artifact", "planning"),
    "PRD.md": ("planning-artifact", "planning"),
    "Plan.md": ("planning-artifact", "planning"),
    "Implement.md": ("execution-artifact", "execution"),
    "Documentation.md": ("execution-artifact", "execution"),
    "Subagent-Manifest.md": ("coordination-artifact", "execution"),
    "Automation-Intent.md": ("coordination-artifact", "execution"),
    "Design-Options.md": ("planning-artifact", "planning"),
}

TRACKED_GLOBS = [
    (".codex/manifests/*.yaml", "manifest", "governance"),
    (".codex/playbooks/*.md", "playbook", "governance"),
    (".codex/reviews/*.md", "review-artifact", "review"),
    (".codex/audits/*.md", "audit-artifact", "audit"),
    (".codex/skills/_proposed/*.md", "proposed-skill", "evolution"),
]


def state_path(root: Path | None = None) -> Path:
    return (root or event_log.repo_root()) / STATE_FILE


def _file_signature(path: Path) -> str:
    digest = hashlib.sha1()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def load_state(root: Path | None = None) -> dict:
    path = state_path(root)
    if not path.exists():
        return {"files": {}}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"files": {}}
    if not isinstance(payload, dict):
        return {"files": {}}
    files = payload.get("files", {})
    if not isinstance(files, dict):
        files = {}
    payload["files"] = files
    return payload


def save_state(payload: dict, root: Path | None = None) -> Path:
    path = state_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = dict(payload)
    payload["synced_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def iter_tracked(root: Path):
    for rel, (category, stage) in TRACKED_FILES.items():
        path = root / rel
        if path.exists() and path.is_file():
            yield rel, path, category, stage
    for pattern, category, stage in TRACKED_GLOBS:
        for path in sorted(root.glob(pattern)):
            if path.is_file():
                yield str(path.relative_to(root)), path, category, stage


def sync(root: Path | None = None, actor: str = "filesystem-bridge", backfill: bool = False) -> list[str]:
    resolved_root = root or event_log.repo_root()
    previous = load_state(resolved_root)
    previous_files = previous.get("files", {})

    current_files: dict[str, str] = {}
    changed: list[str] = []
    tracked = list(iter_tracked(resolved_root))

    for rel, path, category, stage in tracked:
        signature = _file_signature(path)
        current_files[rel] = signature
        if previous_files.get(rel) == signature:
            continue
        changed.append(rel)
        if previous_files or backfill:
            summary = f"{category} {'created' if rel not in previous_files else 'updated'}: {rel}"
            event_log.append_event(
                kind="artifact-sync",
                actor=actor,
                summary=summary,
                files=[rel],
                stage=stage,
                detail={
                    "category": category,
                    "source": "filesystem-bridge",
                    "signature": signature,
                },
                root=resolved_root,
            )

    save_state({"files": current_files}, resolved_root)
    if not previous_files and not backfill:
        return []
    return changed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("cmd", choices=["sync"], nargs="?", default="sync")
    parser.add_argument("--actor", default="filesystem-bridge")
    parser.add_argument("--backfill", action="store_true")
    args = parser.parse_args()

    changed = sync(actor=args.actor, backfill=args.backfill)
    if changed:
        for rel in changed:
            print(rel)
    else:
        print("0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
