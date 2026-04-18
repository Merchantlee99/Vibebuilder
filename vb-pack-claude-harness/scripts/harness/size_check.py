#!/usr/bin/env python3
"""
size_check.py — Parse tool_input from hook stdin and report change size.

Emits a tab-separated line on stdout:
    <added>\t<removed>\t<total>\t<tier>\t<file_path>\t<complexity>

Tier axis (quantity): trivial / normal / high-risk
Complexity axis (quality): simple / complex

Orthogonal — a trivial change can still be complex (e.g. lock ordering fix),
and a high-risk change can be simple (e.g. big CRUD scaffold).
"""

from __future__ import annotations

import difflib
import json
import os
import re
import sys
from pathlib import Path
from typing import Optional


HIGH_RISK_PATH_PATTERNS = [
    r"(^|/)migrations/",
    r"(^|/)infra/",
    r"(^|/)\.github/workflows/",
    r"(^|/)Dockerfile(\.|$)",
    r"(^|/)terraform/",
    r"(^|/)k8s/",
    r"(^|/)security/",
    r"(^|/)auth/",
    r"(^|/)payment/",
    r"(^|/)billing/",
]


HIGH_RISK_CONTENT_MARKERS = [
    "security", "secret", "credential", "password", "auth",
    "billing", "payment", "migration", "public api",
]


COMPLEXITY_MARKERS = [
    # concurrency / state
    "lock", "mutex", "atomic", "concurrent", "goroutine",
    "race condition", "deadlock", "semaphore", "thread",
    # cache / consistency
    "cache invalidation", "eviction", "consistency", "stale",
    # transactions / data flow
    "transaction", "rollback", "isolation level", "idempoten",
    # architecture
    "state machine", "reducer", "event sourcing", "cqrs",
    "dependency injection", "circular import",
    # performance
    "o(n^2", "bottleneck", "profiling", "benchmark",
    "memoize", "memoization", "hot path",
    # refactors
    "refactor", "rename across", "extract module",
]


def _normalize_path(raw_path: str, root: Path) -> str:
    path = (raw_path or "").replace("\\", "/")
    while path.startswith("./"):
        path = path[2:]
    if not path:
        return ""
    if os.path.isabs(path):
        try:
            relative = os.path.relpath(path, root)
        except ValueError:
            relative = path
        if not relative.startswith("../") and relative != "..":
            path = relative.replace("\\", "/")
    return path


def _find_repo_root(start: Optional[Path] = None) -> Path:
    current = (start or Path.cwd()).resolve()
    for candidate in (current, *current.parents):
        if (candidate / ".git").exists() or (candidate / ".claude").exists():
            return candidate
    return current


def _diff_loc(old_text: str, new_text: str) -> tuple[int, int]:
    old_lines = old_text.splitlines()
    new_lines = new_text.splitlines()
    added = removed = 0
    matcher = difflib.SequenceMatcher(a=old_lines, b=new_lines)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "insert":
            added += j2 - j1
        elif tag == "delete":
            removed += i2 - i1
        elif tag == "replace":
            removed += i2 - i1
            added += j2 - j1
    return added, removed


def classify_tier(
    file_path: str, total_loc: int, content_sample: str = "", session_file_count: int = 1,
) -> str:
    normalized = file_path.replace("\\", "/")
    for pattern in HIGH_RISK_PATH_PATTERNS:
        if re.search(pattern, normalized, re.IGNORECASE):
            return "high-risk"
    blob = (content_sample or "").lower()
    for marker in HIGH_RISK_CONTENT_MARKERS:
        if marker in blob:
            return "high-risk"
    if total_loc <= 20 and session_file_count <= 1:
        return "trivial"
    if total_loc <= 100 and session_file_count <= 5:
        return "normal"
    return "high-risk"


def classify_complexity(file_path: str, content_sample: str = "") -> str:
    """Return 'simple' or 'complex'. Used for Layer 4 routing (Opus spike)."""
    blob = (file_path + "\n" + (content_sample or "")).lower()
    for marker in COMPLEXITY_MARKERS:
        if marker.lower() in blob:
            return "complex"
    return "simple"


def parse_hook_payload(raw: str, root: Path) -> dict:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return {"file_path": "", "old_text": "", "new_text": "", "subagent_type": ""}

    tool_input = payload.get("tool_input", {}) or {}
    raw_path = tool_input.get("file_path", "") or ""
    if not isinstance(raw_path, str):
        raw_path = ""

    old_text = tool_input.get("old_string", "")
    new_text = tool_input.get("new_string", "")
    content = tool_input.get("content", "")
    if not isinstance(old_text, str):
        old_text = ""
    if not isinstance(new_text, str):
        new_text = ""
    if not isinstance(content, str):
        content = ""
    if content and not new_text:
        new_text = content

    subagent_type = tool_input.get("subagent_type", "") or payload.get("subagent_type", "") or ""
    if not isinstance(subagent_type, str):
        subagent_type = ""

    return {
        "file_path": _normalize_path(raw_path, root),
        "old_text": old_text, "new_text": new_text,
        "subagent_type": subagent_type,
    }


def main() -> int:
    root = _find_repo_root()
    raw = sys.stdin.read()
    parsed = parse_hook_payload(raw, root)

    file_path = parsed["file_path"]
    added, removed = _diff_loc(parsed["old_text"], parsed["new_text"])
    total = added + removed

    sample = (parsed["old_text"] + "\n" + parsed["new_text"])[:4000]
    sample = file_path + "\n" + sample

    tier = classify_tier(
        file_path=file_path, total_loc=total, content_sample=sample, session_file_count=1,
    )
    complexity = classify_complexity(file_path=file_path, content_sample=sample)

    print(f"{added}\t{removed}\t{total}\t{tier}\t{file_path}\t{complexity}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
