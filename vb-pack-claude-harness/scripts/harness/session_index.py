#!/usr/bin/env python3
"""
session_index.py — Layer 4: SQLite FTS5 search over events + learnings + reviews.

Inspired by hermes-agent's hermes_state.py SessionDB. Builds a searchable
index of past decisions so reviewers can recall "how did we handle this file
before?" and insights_engine can correlate patterns across sessions.

CLI:
  python3 scripts/harness/session_index.py build   # rebuild from scratch
  python3 scripts/harness/session_index.py search "<query>"
  python3 scripts/harness/session_index.py stats

TODO(v1):
  - incremental indexing (track last_ts per corpus)
  - reviewer-aware ranking (same file + same author)
  - integration with memory_manager.prefetch_context
"""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path


DB_RELATIVE = ".claude/memory/session-index.sqlite"


SCHEMA = """
CREATE VIRTUAL TABLE IF NOT EXISTS documents USING fts5(
    source,      -- 'events' | 'learnings' | 'reviews' | 'direction-checks' | 'spikes'
    ts UNINDEXED,
    session_id,
    path,
    body,
    tokenize='porter unicode61'
);
"""


def _find_root(start=None) -> Path:
    current = (Path(start) if start else Path.cwd()).resolve()
    for candidate in (current, *current.parents):
        if (candidate / ".git").exists() or (candidate / ".claude").exists():
            return candidate
    return current


def _open_db(root: Path) -> sqlite3.Connection:
    db_path = root / DB_RELATIVE
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.executescript(SCHEMA)
    return conn


def build_index(repo_root: Path | None = None) -> int:
    root = repo_root or _find_root()
    sys.path.insert(0, str(root / "scripts" / "harness"))
    try:
        import event_log, learning_log
    except Exception:
        return 0

    conn = _open_db(root)
    cur = conn.cursor()
    cur.execute("DELETE FROM documents")

    count = 0
    for e in event_log.iter_all_events(repo_root=root):
        body = json.dumps(e, ensure_ascii=False)
        cur.execute(
            "INSERT INTO documents(source, ts, session_id, path, body) VALUES (?,?,?,?,?)",
            ("events", e.get("ts", ""), e.get("session", ""), e.get("file", ""), body),
        )
        count += 1

    for l in learning_log.load_recent(limit=10000, repo_root=root):
        body = json.dumps(l, ensure_ascii=False)
        cur.execute(
            "INSERT INTO documents(source, ts, session_id, path, body) VALUES (?,?,?,?,?)",
            ("learnings", l.get("ts", ""), l.get("session", ""),
             (l.get("context") or {}).get("file", ""), body),
        )
        count += 1

    # index reviews / direction-checks / spikes
    for subdir, source in (
        ("reviews", "reviews"),
        ("direction-checks", "direction-checks"),
        ("spikes", "spikes"),
    ):
        base = root / ".claude" / subdir
        if not base.exists():
            continue
        for f in base.rglob("*.md"):
            try:
                body = f.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            cur.execute(
                "INSERT INTO documents(source, ts, session_id, path, body) VALUES (?,?,?,?,?)",
                (source, f.stat().st_mtime, "", str(f.relative_to(root)), body),
            )
            count += 1

    conn.commit()
    conn.close()
    return count


def search(query: str, repo_root: Path | None = None, limit: int = 20) -> list[dict]:
    root = repo_root or _find_root()
    db_path = root / DB_RELATIVE
    if not db_path.exists():
        return []
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    cur.execute(
        "SELECT source, ts, session_id, path, substr(body,1,200) FROM documents "
        "WHERE documents MATCH ? LIMIT ?",
        (query, limit),
    )
    rows = [
        {"source": r[0], "ts": r[1], "session_id": r[2], "path": r[3], "snippet": r[4]}
        for r in cur.fetchall()
    ]
    conn.close()
    return rows


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: session_index.py {build|search|stats} [args]", file=sys.stderr)
        return 2
    cmd = sys.argv[1]
    if cmd == "build":
        count = build_index()
        print(f"indexed {count} documents")
        return 0
    if cmd == "search":
        if len(sys.argv) < 3:
            print("usage: session_index.py search <query>", file=sys.stderr)
            return 2
        results = search(sys.argv[2])
        for r in results:
            print(f"[{r['source']}] {r['ts']} {r['path']} — {r['snippet'][:100]}")
        return 0
    if cmd == "stats":
        root = _find_root()
        db_path = root / DB_RELATIVE
        if not db_path.exists():
            print("index not built")
            return 0
        conn = sqlite3.connect(str(db_path))
        cur = conn.cursor()
        cur.execute("SELECT source, COUNT(*) FROM documents GROUP BY source")
        for row in cur.fetchall():
            print(f"{row[0]}: {row[1]}")
        conn.close()
        return 0
    print(f"unknown: {cmd}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
