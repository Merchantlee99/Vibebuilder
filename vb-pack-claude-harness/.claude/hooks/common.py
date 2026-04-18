#!/usr/bin/env python3
"""
common.py — Shared helpers for all hooks (session_start, user_prompt_submit,
pre/post_tool_use, stop). Imports harness Python modules from ../../scripts/.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Optional


def resolve_repo_root(hook_cwd: Optional[str] = None) -> Path:
    """Find the project root. Prefer git toplevel, then .claude ancestor."""
    candidates = []
    if hook_cwd:
        candidates.append(Path(hook_cwd))
    candidates.append(Path.cwd())
    for start in candidates:
        try:
            current = start.resolve()
        except Exception:
            continue
        for candidate in (current, *current.parents):
            if (candidate / ".git").exists() or (candidate / ".claude").exists():
                return candidate
    return Path.cwd()


def harness_import_path(repo_root: Path) -> Path:
    """Path to scripts/harness/ for sys.path injection."""
    return repo_root / "scripts" / "harness"


def ensure_harness_importable(repo_root: Path) -> None:
    p = str(harness_import_path(repo_root))
    if p not in sys.path:
        sys.path.insert(0, p)


def load_event(stream: Optional[Any] = None) -> dict:
    """Parse the Claude Code hook JSON payload from stdin."""
    src = stream if stream is not None else sys.stdin
    try:
        data = src.read()
    except Exception:
        return {}
    if not data:
        return {}
    try:
        return json.loads(data)
    except json.JSONDecodeError:
        return {}


def extract_tool_name(event: dict) -> str:
    v = event.get("tool_name", "")
    return v if isinstance(v, str) else ""


def extract_tool_input(event: dict) -> dict:
    v = event.get("tool_input", {})
    return v if isinstance(v, dict) else {}


def extract_paths(event: dict) -> list[str]:
    ti = extract_tool_input(event)
    out: list[str] = []
    for key in ("file_path", "notebook_path", "path"):
        v = ti.get(key)
        if isinstance(v, str) and v:
            out.append(v)
    return out


def normalize_repo_path(repo_root: Path, raw_path: str) -> str:
    if not raw_path:
        return ""
    path = raw_path.replace("\\", "/")
    while path.startswith("./"):
        path = path[2:]
    if os.path.isabs(path):
        try:
            rel = os.path.relpath(path, str(repo_root))
        except ValueError:
            return path
        if rel.startswith("../") or rel == "..":
            return path
        return rel.replace("\\", "/")
    return path


def tool_mutates_repo(tool_name: str) -> bool:
    return tool_name in {"Edit", "Write", "NotebookEdit"}


def load_runtime(repo_root: Path) -> tuple[Optional[dict], Path]:
    path = repo_root / ".claude" / "runtime.json"
    if not path.exists():
        return None, path
    try:
        return json.loads(path.read_text(encoding="utf-8")), path
    except json.JSONDecodeError:
        return {"_invalid": True}, path


def save_runtime(repo_root: Path, runtime: dict) -> None:
    path = repo_root / ".claude" / "runtime.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(runtime, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def emit_continue(
    *,
    system_message: str = "",
    additional_context: str = "",
    event_name: str = "",
) -> None:
    """Signal Claude Code to continue (no block). Exit 0."""
    if system_message or additional_context:
        payload = {}
        if system_message:
            payload["systemMessage"] = system_message
        if additional_context:
            payload["hookSpecificOutput"] = {
                "hookEventName": event_name,
                "additionalContext": additional_context,
            }
        if payload:
            sys.stdout.write(json.dumps(payload) + "\n")
    sys.exit(0)


def emit_block(reason: str) -> None:
    """Signal Claude Code to block the tool call. Exit 2."""
    sys.stderr.write(reason + "\n")
    sys.exit(2)


# ── protected paths (Layer 3: Gate ⑦) ─────────────────────────────────
# Single source of truth lives in scripts/harness/protected_paths.py.
# That module is imported lazily so hooks still work if scripts/ is missing.

def _load_protected():
    try:
        import sys as _sys
        from pathlib import Path as _P
        _sys.path.insert(0, str(_P(__file__).resolve().parents[2] / "scripts" / "harness"))
        from protected_paths import PROTECTED_REGEX as _PR  # type: ignore
        return _PR
    except Exception:
        # Fallback — minimal set. Should never happen in a sane install.
        return [
            re.compile(r"^\.claude/hooks/"),
            re.compile(r"^\.claude/sealed-prompts/"),
            re.compile(r"^\.claude/runtime\.json$"),
            re.compile(r"^scripts/harness/"),
            re.compile(r"^CLAUDE\.md$"),
        ]


PROTECTED_REGEX = _load_protected()


def is_protected_path(rel_path: str) -> Optional[re.Pattern]:
    for pat in PROTECTED_REGEX:
        if pat.search(rel_path):
            return pat
    return None


# ── size_check dispatch ───────────────────────────────────────────────


def run_size_check(repo_root: Path, payload_raw: str) -> dict:
    """Invoke scripts/harness/size_check.py with payload on stdin.

    Returns dict with: added, removed, total, tier, file_path, complexity.
    """
    ensure_harness_importable(repo_root)
    try:
        import size_check  # type: ignore
    except Exception:
        return {"added": 0, "removed": 0, "total": 0,
                "tier": "normal", "file_path": "", "complexity": "simple"}

    root = size_check._find_repo_root()
    parsed = size_check.parse_hook_payload(payload_raw, root)
    file_path = parsed["file_path"]
    added, removed = size_check._diff_loc(parsed["old_text"], parsed["new_text"])
    total = added + removed
    sample = (parsed["old_text"] + "\n" + parsed["new_text"])[:4000]
    sample = file_path + "\n" + sample
    tier = size_check.classify_tier(
        file_path=file_path, total_loc=total,
        content_sample=sample, session_file_count=1,
    )
    complexity = size_check.classify_complexity(file_path=file_path, content_sample=sample)
    return {
        "added": added, "removed": removed, "total": total,
        "tier": tier, "file_path": file_path, "complexity": complexity,
    }
