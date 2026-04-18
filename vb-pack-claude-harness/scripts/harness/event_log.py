#!/usr/bin/env python3
"""
event_log.py — Append-only event logger for the Unified 4-axis harness.

Writes structured events to .claude/events.jsonl with atomic append.
Used by all hooks to record what happened, who acted, what was touched.

The event log is the source of truth for meta-audit; it is NOT modifiable
by AI (enforced by Gate ⑦).
"""

from __future__ import annotations

import gzip
import json
import os
import sys
import time
import uuid
from pathlib import Path
from typing import Any, Optional


HARNESS_DIR_NAME = ".claude"
EVENT_LOG_NAME = "events.jsonl"
EPHEMERAL_SESSION_SUBDIR = ".claude/ephemeral"
EPHEMERAL_SESSION_FALLBACK_DIR = "/tmp"
EPHEMERAL_SESSION_PREFIX = "claude-harness-ephemeral-session-"


# In-process memo — survives disk-write failures within a single process.
# Without this, all-candidates-unwritable paths mint a fresh UUID per call
# and break per-session Gate ⑥ / Gate ② correlation.
_SESSION_ID_MEMO: Optional[str] = None


def _resolve_session_id() -> str:
    """Return a non-empty, **stable-within-process** session id.

    Resolution order (first success wins, then memoized):
      1. CLAUDE_SESSION_ID env var
      2. In-process memo from earlier call
      3. Project-local day cache (survives reboots / tmp cleaners)
      4. /tmp day cache fallback
      5. Process-level tempdir fallback (tempfile.gettempdir)
      6. Newly minted ephemeral-<uuid12> — persisted to first writable
         candidate, then always memoized so subsequent calls match.
    """
    global _SESSION_ID_MEMO

    sid = os.environ.get("CLAUDE_SESSION_ID", "").strip()
    if sid:
        _SESSION_ID_MEMO = sid
        return sid

    if _SESSION_ID_MEMO:
        return _SESSION_ID_MEMO

    day = time.strftime("%Y%m%d", time.gmtime())
    filename = f"{EPHEMERAL_SESSION_PREFIX}{day}.id"

    candidates: list[Path] = []
    try:
        root = _find_repo_root()
        candidates.append(root / EPHEMERAL_SESSION_SUBDIR / filename)
    except Exception:
        pass
    candidates.append(Path(EPHEMERAL_SESSION_FALLBACK_DIR) / filename)
    try:
        import tempfile
        candidates.append(Path(tempfile.gettempdir()) / filename)
    except Exception:
        pass

    for cache in candidates:
        try:
            if cache.exists():
                cached = cache.read_text(encoding="utf-8").strip()
                if cached:
                    _SESSION_ID_MEMO = cached
                    return cached
        except OSError:
            continue

    new_sid = f"ephemeral-{uuid.uuid4().hex[:12]}"
    for cache in candidates:
        try:
            cache.parent.mkdir(parents=True, exist_ok=True)
            cache.write_text(new_sid, encoding="utf-8")
            break
        except OSError:
            continue
    # Memoize regardless of whether persist succeeded — in-process stability
    # is the invariant Gate ⑥ depends on.
    _SESSION_ID_MEMO = new_sid
    return new_sid


def _find_repo_root(start: Optional[Path] = None) -> Path:
    current = (start or Path.cwd()).resolve()
    for candidate in (current, *current.parents):
        if (candidate / ".git").exists() or (candidate / HARNESS_DIR_NAME).exists():
            return candidate
    return current


def event_log_path(repo_root: Optional[Path] = None) -> Path:
    root = repo_root or _find_repo_root()
    return root / HARNESS_DIR_NAME / EVENT_LOG_NAME


def iter_all_events(repo_root: Optional[Path] = None,
                     include_synthesized: bool = True):
    """Yield every event from all segments + the live file, in order.

    Rotation creates `events.jsonl.seg-<ts>` (optionally .gz). Any reader
    that needs historical state MUST iterate via this helper.

    include_synthesized=False filters out events with `detail.synthesized=True`
    (events recovered by activity_replay.py after a hook-gap window).
    Gate ⑥ scope accumulation should use False to avoid counting replayed
    edits as real cumulative LOC.
    """
    live = event_log_path(repo_root)
    parent = live.parent
    if not parent.exists():
        return
    segments = sorted(parent.glob(f"{live.name}.seg-*"))

    def _iter_file(path):
        if path.suffix == ".gz":
            opener = lambda p: gzip.open(p, "rt", encoding="utf-8")
        else:
            opener = lambda p: open(p, "r", encoding="utf-8")
        try:
            with opener(path) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        ev = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if not include_synthesized:
                        detail = ev.get("detail") or {}
                        if detail.get("synthesized"):
                            continue
                    yield ev
        except OSError:
            return

    for seg in segments:
        yield from _iter_file(seg)
    if live.exists():
        yield from _iter_file(live)


def append_event(
    gate: str,
    outcome: str,
    actor: str = "unknown",
    file_path: str = "",
    detail: Optional[dict] = None,
    repo_root: Optional[Path] = None,
) -> Path:
    """Append one event line to .claude/events.jsonl."""
    path = event_log_path(repo_root)
    path.parent.mkdir(parents=True, exist_ok=True)

    entry: dict[str, Any] = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "gate": gate,
        "outcome": outcome,
        "actor": actor,
        "file": file_path or "",
        "session": _resolve_session_id(),
        "detail": detail or {},
    }

    with open(path, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
        handle.flush()
        os.fsync(handle.fileno())

    return path


def main() -> int:
    """CLI entry: append an event from argv/stdin.

    Usage: event_log.py <gate> <outcome> [actor] [file] < detail.json
    """
    if len(sys.argv) < 3:
        print("usage: event_log.py <gate> <outcome> [actor] [file] < detail.json", file=sys.stderr)
        return 2

    gate = sys.argv[1]
    outcome = sys.argv[2]
    actor = sys.argv[3] if len(sys.argv) > 3 else "unknown"
    file_path = sys.argv[4] if len(sys.argv) > 4 else ""

    detail: dict = {}
    if not sys.stdin.isatty():
        try:
            raw = sys.stdin.read().strip()
            if raw:
                detail = json.loads(raw)
        except json.JSONDecodeError as exc:
            print(f"warn: invalid detail JSON, ignoring: {exc}", file=sys.stderr)
            detail = {"raw_parse_error": str(exc)}

    path = append_event(
        gate=gate, outcome=outcome, actor=actor, file_path=file_path, detail=detail,
    )
    print(str(path))
    return 0


if __name__ == "__main__":
    sys.exit(main())
