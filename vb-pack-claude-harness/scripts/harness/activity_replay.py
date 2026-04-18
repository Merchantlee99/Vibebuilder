#!/usr/bin/env python3
"""
activity_replay.py — Reconstruct events for time windows when hooks were
disabled (circuit breaker tripped OR manual disable).

When a hook is disabled, edits still happen but no `edit-tracked` /
`review-needed` events are recorded. This script scans git reflog +
commit history since the hook disabled_ts and synthesizes advisory
events so the timeline is not silently missing chunks.

Emits:
  - gate=system outcome=hook-gap-detected   (per disabled window)
  - gate=06 outcome=edit-tracked actor=replay file=<path>  (per touched file)

All synthesized events carry `"synthesized": true` in detail so they
can be filtered out of strict gate checks if needed.

Usage:
  python3 scripts/harness/activity_replay.py scan      # detect + emit
  python3 scripts/harness/activity_replay.py --dry-run # report without writing
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "harness"))


def _load_runtime() -> dict:
    rt = REPO_ROOT / ".claude" / "runtime.json"
    if not rt.exists():
        return {}
    try:
        return json.loads(rt.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _parse_ts(s: str) -> dt.datetime | None:
    try:
        return dt.datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=dt.timezone.utc)
    except Exception:
        return None


def _find_gap_windows() -> list[tuple[str, dt.datetime, dt.datetime]]:
    """Return [(hook_name, disabled_from, last_success_after)].

    Heuristic: hook_health.last_failure_ts or last_success_ts gaps + current
    disabled state. We approximate:
      - If currently disabled: gap = (last_success_ts, now)
      - Else: no known gap at replay time
    """
    runtime = _load_runtime()
    health = runtime.get("hook_health", {}) or {}
    now = dt.datetime.now(dt.timezone.utc)
    gaps: list[tuple[str, dt.datetime, dt.datetime]] = []
    for hook, state in health.items():
        if not state.get("disabled"):
            continue
        last_ok = _parse_ts(state.get("last_success_ts", "") or "")
        if last_ok is None:
            continue
        if (now - last_ok).total_seconds() < 60:
            continue  # trivial gap
        gaps.append((hook, last_ok, now))
    return gaps


def _git_touched_files_since(cutoff: dt.datetime) -> list[tuple[str, str, str]]:
    """Return [(path, commit_sha, commit_ts_iso)] for files changed after cutoff."""
    iso = cutoff.strftime("%Y-%m-%dT%H:%M:%SZ")
    try:
        r = subprocess.run(
            ["git", "log", f"--since={iso}", "--name-only", "--pretty=format:%H %cI"],
            cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=10,
        )
    except Exception:
        return []
    if r.returncode != 0:
        return []
    out: list[tuple[str, str, str]] = []
    sha, ts = "", ""
    for line in r.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        if " " in line and len(line.split()[0]) == 40:
            parts = line.split(None, 1)
            sha = parts[0]
            ts = parts[1] if len(parts) > 1 else ""
            continue
        if sha:
            out.append((line, sha, ts))
    return out


def _git_unstaged_files() -> list[str]:
    try:
        r = subprocess.run(["git", "status", "--porcelain"],
                            cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=10)
    except Exception:
        return []
    if r.returncode != 0:
        return []
    files = []
    for line in r.stdout.splitlines():
        line = line.rstrip()
        if len(line) > 3:
            files.append(line[3:].strip())
    return files


def scan(dry_run: bool) -> int:
    gaps = _find_gap_windows()
    if not gaps:
        print("  (no hook-gap windows detected)")
        return 0

    import event_log  # type: ignore
    total_replayed = 0
    for hook, start, end in gaps:
        touched = _git_touched_files_since(start)
        unstaged = _git_unstaged_files()
        unique_files = sorted({f for f, _, _ in touched} | set(unstaged))

        print(f"  hook={hook} window={start.isoformat()} → {end.isoformat()}")
        print(f"    touched: {len(unique_files)} file(s) (committed={len(touched)}, "
              f"unstaged={len(unstaged)})")
        if dry_run:
            continue

        # Window marker
        event_log.append_event(
            gate="system", outcome="hook-gap-detected", actor="replay",
            file_path=hook,
            detail={"hook": hook, "window_start": start.isoformat(),
                    "window_end": end.isoformat(),
                    "touched_file_count": len(unique_files),
                    "synthesized": True},
            repo_root=REPO_ROOT,
        )

        for f in unique_files:
            event_log.append_event(
                gate="06", outcome="edit-tracked", actor="replay",
                file_path=f,
                detail={"reason": "hook-gap-replay", "hook_gap": hook,
                        "synthesized": True, "window_start": start.isoformat()},
                repo_root=REPO_ROOT,
            )
            total_replayed += 1

    print(f"\n  total replayed events: {total_replayed} "
          f"({'dry-run' if dry_run else 'appended to events.jsonl'})")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", nargs="?", default="scan", choices=("scan",))
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    return scan(args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
