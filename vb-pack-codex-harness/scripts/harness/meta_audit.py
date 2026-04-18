#!/usr/bin/env python3
"""Trigger a pending audit when telemetry suggests the harness needs review."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
from pathlib import Path

from event_log import append_event, iter_events, repo_root
from learning_log import load_recent


ROLLBACK_PATTERNS = [
    r"\brevert\b",
    r"\brollback\b",
    r"\bhotfix\b",
    r"\bemergency\b",
]


def git_signals(root: Path) -> list[str]:
    proc = subprocess.run(
        ["git", "log", "--since=7.days.ago", "--pretty=format:%s"],
        cwd=str(root),
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        return []
    hits: list[str] = []
    for subject in proc.stdout.splitlines():
        for pattern in ROLLBACK_PATTERNS:
            if re.search(pattern, subject, re.IGNORECASE):
                hits.append(subject)
                break
    return hits


def evaluate(root: Path) -> list[str]:
    triggers: list[str] = []
    events = list(iter_events(root) or [])
    if len(events) >= 40:
        kinds = {event.get("kind") for event in events[-40:] if event.get("kind")}
        if len(kinds) >= 3:
            triggers.append("rolling window contains 3+ event kinds")
    if len(events) >= 150:
        triggers.append("150+ events recorded since repo start")

    learnings = load_recent(limit=200, root=root)
    counts: dict[str, int] = {}
    for learning in learnings:
        pattern = str(learning.get("pattern", ""))
        if not pattern:
            continue
        counts[pattern] = counts.get(pattern, 0) + 1
    for pattern, count in counts.items():
        if count >= 5:
            triggers.append(f"pattern repeated 5+ times: {pattern}")
            break

    for subject in git_signals(root):
        triggers.append(f"rollback-like git signal: {subject}")
        break

    request_file = root / ".codex" / "audits" / "requested.txt"
    if request_file.exists():
        triggers.append("manual audit request file exists")
    return triggers


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply-trigger", action="store_true")
    args = parser.parse_args()

    root = repo_root()
    triggers = evaluate(root)
    if not triggers:
        print("no-trigger")
        return 0

    print("TRIGGERED")
    for trigger in triggers:
        print(f"- {trigger}")

    if not args.apply_trigger:
        return 0

    audits_dir = root / ".codex" / "audits"
    audits_dir.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    pending = audits_dir / f"meta-audit-pending-{stamp}.md"
    lines = ["# Meta Audit Pending", "", f"Triggered at {stamp}.", "", "## Triggers", ""]
    lines.extend(f"- {trigger}" for trigger in triggers)
    lines.append("")
    lines.append("Review manifests, docs, and repeated failure patterns before continuing major harness changes.")
    pending.write_text("\n".join(lines) + "\n", encoding="utf-8")

    append_event(
        kind="audit-triggered",
        actor="system",
        summary="meta audit pending file created",
        files=[str(pending.relative_to(root))],
        stage="audit",
        detail={"triggers": triggers},
        root=root,
    )
    print(pending)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
