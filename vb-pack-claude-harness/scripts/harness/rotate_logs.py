#!/usr/bin/env python3
"""
rotate_logs.py — Segmented append-only rotation for events.jsonl and
learnings.jsonl.

Design: NEVER rewrite the live file with a marker. Instead, rename the
current file to `<name>.seg-<ts>` and create a fresh empty live file.
Readers union segments+live via event_log.iter_all_events().
"""

from __future__ import annotations

import datetime as dt
import gzip
import os
import shutil
import sys
import time
from pathlib import Path


EVENTS_THRESHOLD_BYTES = 5 * 1024 * 1024      # 5 MB
LEARNINGS_THRESHOLD_BYTES = 1 * 1024 * 1024   # 1 MB
GZIP_AFTER_DAYS = 7


def _find_repo_root(start=None) -> Path:
    current = (Path(start) if start else Path.cwd()).resolve()
    for candidate in (current, *current.parents):
        if (candidate / ".git").exists() or (candidate / ".claude").exists():
            return candidate
    return current


def rotate(path: Path, threshold: int, kind: str) -> bool:
    if not path.exists():
        return False
    size = path.stat().st_size
    if size < threshold:
        return False
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    segment = path.with_name(f"{path.name}.seg-{stamp}")
    os.rename(path, segment)
    path.touch()
    print(f"rotated {path.name}: {size} bytes → segment {segment.name}")
    return True


def gzip_old_segments(dir_path: Path) -> int:
    if not dir_path.exists():
        return 0
    cutoff = time.time() - GZIP_AFTER_DAYS * 86400
    count = 0
    for seg in dir_path.glob("*.seg-*"):
        if seg.suffix == ".gz":
            continue
        if seg.stat().st_mtime < cutoff:
            gz = seg.with_suffix(seg.suffix + ".gz")
            with open(seg, "rb") as src, gzip.open(gz, "wb", compresslevel=6) as dst:
                shutil.copyfileobj(src, dst)
            seg.unlink()
            count += 1
    return count


def main() -> int:
    root = _find_repo_root()
    ev = root / ".claude" / "events.jsonl"
    lr = root / ".claude" / "learnings.jsonl"

    rotated = False
    rotated |= rotate(ev, EVENTS_THRESHOLD_BYTES, "events")
    rotated |= rotate(lr, LEARNINGS_THRESHOLD_BYTES, "learnings")
    gzipped = gzip_old_segments(root / ".claude")

    if rotated or gzipped > 0:
        sys.path.insert(0, str(root / "scripts" / "harness"))
        try:
            import event_log
            event_log.append_event(
                gate="system", outcome="log-rotation-run", actor="system",
                file_path=".claude/",
                detail={"events_rotated": rotated and ev.exists(),
                        "learnings_rotated": rotated and lr.exists(),
                        "segments_gzipped": gzipped,
                        "invariant": "append-only preserved"},
            )
        except Exception:
            pass
    else:
        print("no rotation needed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
