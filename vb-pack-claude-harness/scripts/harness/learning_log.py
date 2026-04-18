#!/usr/bin/env python3
"""
learning_log.py — Append-only learning recorder.

Writes to .claude/learnings.jsonl when Gate ② review finds problems or when
the same failure repeats (Gate ③ trigger). Loaded by Gate ⑤ at session start
AND by Layer 4 memory_manager.py pre-turn hook.

FAILURE_TAXONOMY is a controlled vocabulary. Unknown patterns are accepted
but tagged with context.pattern_validated=false for meta-audit to review.
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Iterable, Optional


HARNESS_DIR_NAME = ".claude"
LEARNING_LOG_NAME = "learnings.jsonl"


FAILURE_TAXONOMY = frozenset([
    # scope / spec
    "scope-drift",
    "ambiguous-spec",
    "wrong-abstraction-level",
    # dependency / impact
    "hidden-dependency",
    "partial-fix-broke-neighbor",
    "cross-module-drift",
    # testing / verification
    "test-passed-contract-violated",
    "test-oracle-manipulated",
    "no-test-for-change",
    # tooling / environment
    "tool-misuse",
    "env-assumption-mismatch",
    "bash-bypass",
    # gate-specific
    "self-review-attempt",
    "protected-path-probe",
    "stub-review",
    "injection-candidate",
    # routing (Layer 4 complexity signal)
    "secondary-stuck-retry-2x",
    "opus-spike-mismatch",
    # operational
    "doc-impl-drift",
    "rollback-triggered",
    "harness-init",
    # hermes-inspired
    "skill-drift",
    "memory-overfit",
])


def _find_repo_root(start: Optional[Path] = None) -> Path:
    current = (start or Path.cwd()).resolve()
    for candidate in (current, *current.parents):
        if (candidate / ".git").exists() or (candidate / HARNESS_DIR_NAME).exists():
            return candidate
    return current


def _session_id() -> str:
    try:
        import event_log  # type: ignore
        return event_log._resolve_session_id()
    except Exception:
        return os.environ.get("CLAUDE_SESSION_ID", "")


def learning_log_path(repo_root: Optional[Path] = None) -> Path:
    root = repo_root or _find_repo_root()
    return root / HARNESS_DIR_NAME / LEARNING_LOG_NAME


def append_learning(
    gate: str,
    mistake: str,
    fix: str = "",
    pattern: str = "",
    context: Optional[dict] = None,
    actor: str = "unknown",
    repo_root: Optional[Path] = None,
) -> Path:
    """Append one learning entry."""
    path = learning_log_path(repo_root)
    path.parent.mkdir(parents=True, exist_ok=True)

    # Pattern vocabulary validation. Normalize and check membership.
    normalized = (pattern or "").strip().lower()
    ctx = dict(context or {})
    if normalized and normalized not in FAILURE_TAXONOMY:
        ctx["pattern_validated"] = False
        ctx["pattern_unknown"] = True
    else:
        ctx["pattern_validated"] = True

    entry: dict[str, Any] = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "gate": gate,
        "actor": actor,
        "pattern": normalized,
        "mistake": mistake,
        "fix": fix or "",
        "context": ctx,
        "session": _session_id(),
    }

    with open(path, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
        handle.flush()
        os.fsync(handle.fileno())

    return path


def load_recent(limit: int = 20, repo_root: Optional[Path] = None) -> list[dict]:
    """Return the N most-recent learning entries (oldest-first)."""
    path = learning_log_path(repo_root)
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as handle:
        lines = [ln for ln in handle if ln.strip()]
    tail = lines[-limit:]
    out: list[dict] = []
    for line in tail:
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def load_by_pattern(pattern: str, repo_root: Optional[Path] = None) -> list[dict]:
    path = learning_log_path(repo_root)
    if not path.exists():
        return []
    matches: list[dict] = []
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            if entry.get("pattern") == pattern:
                matches.append(entry)
    return matches


def format_for_prompt(entries: Iterable[dict]) -> str:
    lines: list[str] = []
    for entry in entries:
        ts = entry.get("ts", "?")
        gate = entry.get("gate", "?")
        pattern = entry.get("pattern") or "(no-pattern)"
        mistake = entry.get("mistake", "")
        fix = entry.get("fix", "")
        lines.append(f"- [{ts}] gate={gate} pattern={pattern}")
        if mistake:
            lines.append(f"    mistake: {mistake}")
        if fix:
            lines.append(f"    fix: {fix}")
    return "\n".join(lines) if lines else "(no learnings recorded yet)"


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__, file=sys.stderr)
        return 2
    cmd = sys.argv[1]

    if cmd == "append":
        if len(sys.argv) < 5:
            print("usage: learning_log.py append <gate> <pattern> <mistake> [fix]", file=sys.stderr)
            return 2
        gate = sys.argv[2]
        pattern = sys.argv[3]
        mistake = sys.argv[4]
        fix = sys.argv[5] if len(sys.argv) > 5 else ""
        context: dict = {}
        if not sys.stdin.isatty():
            try:
                raw = sys.stdin.read().strip()
                if raw:
                    context = json.loads(raw)
            except json.JSONDecodeError:
                context = {}
        path = append_learning(
            gate=gate, mistake=mistake, fix=fix, pattern=pattern, context=context,
        )
        print(str(path))
        return 0

    if cmd == "show":
        limit = int(sys.argv[2]) if len(sys.argv) > 2 else 20
        entries = load_recent(limit=limit)
        print(format_for_prompt(entries))
        return 0

    if cmd == "by-pattern":
        if len(sys.argv) < 3:
            print("usage: learning_log.py by-pattern <pattern>", file=sys.stderr)
            return 2
        entries = load_by_pattern(sys.argv[2])
        print(format_for_prompt(entries))
        return 0

    print(f"unknown cmd: {cmd}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
