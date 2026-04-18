#!/usr/bin/env python3
"""
append_only_lock.py — OS-level append-only protection for audit logs.

Layer 3 Gate ⑦ already blocks Claude's Edit/Write on events.jsonl and
learnings.jsonl at the harness level. This script adds a *second* layer
at the filesystem level so that a rogue Bash command (e.g., `> events.jsonl`
to truncate, or `rm events.jsonl`) cannot silently erase history.

Platform support:
  - Linux: uses `chattr +a` (append-only ext4/xfs attribute). Requires sudo.
  - macOS: uses `chflags uappnd` (user append-only flag).
  - Other: no-op, prints a warning.

Usage:
  python3 scripts/harness/append_only_lock.py lock     # enable append-only
  python3 scripts/harness/append_only_lock.py unlock   # disable (needs sudo/admin)
  python3 scripts/harness/append_only_lock.py status   # show current state

Notes:
  - On Linux, `chattr +a` requires CAP_LINUX_IMMUTABLE or root.
  - On macOS, `chflags uappnd` can be set by the owning user without sudo;
    removing it (`nouappnd`) also works without sudo for user flag.
  - The log rotator (rotate_logs.py) must temporarily unlock before segment
    rename. Wrap rotation in try/finally.
  - Failure to apply the lock is non-fatal — the harness-level Gate ⑦
    still applies.

This is a defense-in-depth feature. It does NOT replace Gate ⑦.
"""

from __future__ import annotations

import argparse
import platform
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
TARGETS = [
    REPO_ROOT / ".claude" / "events.jsonl",
    REPO_ROOT / ".claude" / "learnings.jsonl",
]


def _run(cmd: list[str]) -> tuple[int, str]:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        return r.returncode, (r.stdout + r.stderr).strip()
    except Exception as exc:
        return -1, str(exc)


def lock_file(path: Path) -> tuple[bool, str]:
    if not path.exists():
        # Create empty so the lock has a target.
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("", encoding="utf-8")
    system = platform.system()
    if system == "Linux":
        rc, out = _run(["chattr", "+a", str(path)])
        if rc == 0:
            return True, "chattr +a applied"
        return False, f"chattr failed (rc={rc}, need sudo): {out}"
    if system == "Darwin":
        rc, out = _run(["chflags", "uappnd", str(path)])
        if rc == 0:
            return True, "chflags uappnd applied"
        return False, f"chflags failed (rc={rc}): {out}"
    return False, f"unsupported platform: {system} (harness Gate ⑦ still applies)"


def unlock_file(path: Path) -> tuple[bool, str]:
    if not path.exists():
        return True, "file missing (nothing to unlock)"
    system = platform.system()
    if system == "Linux":
        rc, out = _run(["chattr", "-a", str(path)])
        if rc == 0:
            return True, "chattr -a applied"
        return False, f"chattr failed (need sudo): {out}"
    if system == "Darwin":
        rc, out = _run(["chflags", "nouappnd", str(path)])
        if rc == 0:
            return True, "chflags nouappnd applied"
        return False, f"chflags failed: {out}"
    return False, f"unsupported platform: {system}"


def status_file(path: Path) -> tuple[bool, str]:
    if not path.exists():
        return False, "missing"
    system = platform.system()
    if system == "Linux":
        rc, out = _run(["lsattr", str(path)])
        if rc == 0:
            return True, out.split()[0] if out else "(no attrs)"
        return False, f"lsattr failed: {out}"
    if system == "Darwin":
        rc, out = _run(["ls", "-lO", str(path)])
        if rc == 0:
            flagged = "uappnd" in out
            return True, f"uappnd={'yes' if flagged else 'no'} | {out}"
        return False, out
    return False, f"unsupported platform: {system}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("action", choices=("lock", "unlock", "status"))
    args = ap.parse_args()

    fn = {"lock": lock_file, "unlock": unlock_file, "status": status_file}[args.action]
    any_fail = False
    for p in TARGETS:
        ok, msg = fn(p)
        tag = "ok " if ok else "FAIL"
        rel = p.relative_to(REPO_ROOT)
        print(f"  [{tag}] {str(rel):<30} {msg}")
        if not ok and args.action != "status":
            any_fail = True
    return 1 if any_fail else 0


if __name__ == "__main__":
    sys.exit(main())
