#!/usr/bin/env python3
"""Index and search harness session memory."""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
from pathlib import Path

from common import ROOT


INDEX = ROOT / "harness" / "context" / "session-index.sqlite3"
SOURCES = [
    ROOT / "harness" / "telemetry" / "events.jsonl",
    ROOT / "harness" / "telemetry" / "learnings.jsonl",
    ROOT / "docs" / "ai" / "SESSION_LOG.md",
    ROOT / "docs" / "ai" / "decisions.md",
    ROOT / "docs" / "ai" / "known-gaps.md",
]


def connect() -> sqlite3.Connection:
    INDEX.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(INDEX)
    conn.execute("CREATE VIRTUAL TABLE IF NOT EXISTS docs USING fts5(path, kind, body)")
    return conn


def create_schema(conn: sqlite3.Connection) -> None:
    conn.execute("CREATE VIRTUAL TABLE IF NOT EXISTS docs USING fts5(path, kind, body)")


def iter_docs() -> list[tuple[str, str, str]]:
    docs: list[tuple[str, str, str]] = []
    for path in SOURCES:
        if not path.exists():
            continue
        rel = str(path.relative_to(ROOT))
        if path.suffix == ".jsonl":
            for idx, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
                if not line.strip():
                    continue
                try:
                    item = json.loads(line)
                    body = json.dumps(item, ensure_ascii=False, sort_keys=True)
                except json.JSONDecodeError:
                    body = line
                docs.append((f"{rel}:{idx}", path.stem, body))
        else:
            docs.append((rel, path.stem, path.read_text(encoding="utf-8")))
    return docs


def rebuild(_: argparse.Namespace) -> int:
    tmp_index = INDEX.with_suffix(".sqlite3.tmp")
    if tmp_index.exists():
        tmp_index.unlink()
    tmp_conn = sqlite3.connect(tmp_index)
    create_schema(tmp_conn)
    with tmp_conn:
        tmp_conn.executemany("INSERT INTO docs(path, kind, body) VALUES (?, ?, ?)", iter_docs())
    count = tmp_conn.execute("SELECT count(*) FROM docs").fetchone()[0]
    tmp_conn.close()
    os.replace(tmp_index, INDEX)
    print(f"indexed {count} records")
    return 0


def rebuild_in_place(_: argparse.Namespace) -> int:
    conn = connect()
    with conn:
        conn.execute("DELETE FROM docs")
        conn.executemany("INSERT INTO docs(path, kind, body) VALUES (?, ?, ?)", iter_docs())
    count = conn.execute("SELECT count(*) FROM docs").fetchone()[0]
    print(f"indexed {count} records")
    return 0


def search(args: argparse.Namespace) -> int:
    conn = connect()
    rows = conn.execute(
        "SELECT path, kind, snippet(docs, 2, '[', ']', '...', 12) FROM docs WHERE docs MATCH ? LIMIT ?",
        (args.query, args.limit),
    ).fetchall()
    for path, kind, snippet in rows:
        print(f"{path} [{kind}] {snippet}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("rebuild")
    sub.add_parser("rebuild-in-place")
    s = sub.add_parser("search")
    s.add_argument("query")
    s.add_argument("--limit", type=int, default=10)
    args = parser.parse_args()
    if args.command == "rebuild":
        return rebuild(args)
    if args.command == "rebuild-in-place":
        return rebuild_in_place(args)
    if args.command == "search":
        return search(args)
    raise AssertionError(args.command)


if __name__ == "__main__":
    raise SystemExit(main())
