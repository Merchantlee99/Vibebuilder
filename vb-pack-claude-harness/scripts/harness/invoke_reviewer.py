#!/usr/bin/env python3
"""
invoke_reviewer.py — Produce a self-contained brief for the reviewer actor.

The harness does NOT auto-dispatch reviewers. This script bridges the gap:
it reads the most recent unresolved `review-needed` event and prints a copy-
paste-ready brief for the user (or for a fresh isolated Claude Code session
acting as `claude-reviewer`).

Usage:
  python3 scripts/harness/invoke_reviewer.py              # latest review-needed
  python3 scripts/harness/invoke_reviewer.py --file PATH  # pick by target file
  python3 scripts/harness/invoke_reviewer.py --json       # machine-readable

The printed brief contains:
  - the sealed-prompt path the reviewer must follow
  - the target file + diff context to read
  - the exact event_log.py command to record `02 pass <actor>`

Exit 0 = brief printed. Exit 1 = no pending review found.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "harness"))


def _latest_review_needed(target_file: str | None = None) -> dict | None:
    import event_log  # type: ignore
    session_id = event_log._resolve_session_id()

    # Collect review-needed + pass events for this session.
    needed: list[dict] = []
    passed: set[tuple[str, str]] = set()  # (file, review-needed ts)
    for e in event_log.iter_all_events(repo_root=REPO_ROOT):
        if e.get("gate") != "02":
            continue
        if (e.get("session") or "") != session_id:
            continue
        outcome = e.get("outcome")
        if outcome == "review-needed":
            needed.append(e)
        elif outcome == "pass":
            detail = e.get("detail") or {}
            f = detail.get("reviewed_file") or e.get("file", "")
            ts = detail.get("review_needed_ts", "")
            if f and ts:
                passed.add((f, ts))

    # Unresolved = review-needed whose (file, ts) has no matching pass
    unresolved = [e for e in needed if (e.get("file", ""), e.get("ts", "")) not in passed]
    if target_file:
        unresolved = [e for e in unresolved if e.get("file") == target_file]
    return unresolved[-1] if unresolved else None


def _render_brief(event: dict) -> str:
    detail = event.get("detail") or {}
    target = event.get("file", "")
    tier = detail.get("tier", "unknown")
    complexity = detail.get("complexity", "unknown")
    sealed = detail.get("suggested_sealed_prompt", ".claude/sealed-prompts/review-code.md")
    author = event.get("actor", "claude")
    reviewer_expected = detail.get("reviewer_expected", "user")
    review_needed_ts = event.get("ts", "")

    return (
        f"# Reviewer brief — {target}\n\n"
        f"**Author actor**: `{author}` (must differ from reviewer)\n"
        f"**Expected reviewer**: `{reviewer_expected}` "
        f"(or an isolated `claude-reviewer` session)\n"
        f"**Tier**: {tier}  **Complexity**: {complexity}\n"
        f"**Review-needed ts**: {review_needed_ts}\n\n"
        f"## 1. Read the sealed prompt\n"
        f"    cat {sealed}\n\n"
        f"## 2. Inspect the change\n"
        f"    git diff HEAD -- {target}\n"
        f"    sed -n '1,200p' {target}\n\n"
        f"## 3. Write your review\n"
        f"    .claude/reviews/<ts>.md  (must be >=800B, contain Verdict:, "
        f"one File:/Issue:/Evidence: block, and for code: Rollback triggers:)\n\n"
        f"## 4. Record verdict (must use an actor != `{author}`)\n"
        f"    python3 scripts/harness/event_log.py 02 pass <reviewer-actor> "
        f"{target} <<JSON\n"
        f"    {{\n"
        f'      "reviewer_file": ".claude/reviews/<ts>.md",\n'
        f'      "reviewed_file": "{target}",\n'
        f'      "review_needed_ts": "{review_needed_ts}",\n'
        f'      "summary": "<one-line verdict>"\n'
        f"    }}\n"
        f"    JSON\n\n"
        f"## 5. If reviewer is an isolated Claude Code session\n"
        f"Start a fresh session in this repo, then paste:\n"
        f"    You are `claude-reviewer`. Open ONLY:\n"
        f"      - {sealed}   (sealed prompt)\n"
        f"      - {target}   (target file)\n"
        f"      - git diff for {target}\n"
        f"    Do not read any other file from the author session. "
        f"Produce the review per sealed prompt, then output the "
        f"event_log.py command above ready for the user to run.\n"
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", default=None,
                    help="filter to a specific target file path")
    ap.add_argument("--json", action="store_true",
                    help="print the raw review-needed event as JSON")
    args = ap.parse_args()

    event = _latest_review_needed(args.file)
    if event is None:
        msg = "no unresolved review-needed event"
        if args.file:
            msg += f" for {args.file}"
        print(msg, file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(event, indent=2, ensure_ascii=False))
    else:
        print(_render_brief(event))
    return 0


if __name__ == "__main__":
    sys.exit(main())
