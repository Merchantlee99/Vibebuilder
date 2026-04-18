#!/usr/bin/env python3
"""
automation_planner.py — Detect continuation signals and propose automations.

Scans the harness state for conditions that warrant a scheduled / heartbeat
follow-up:

  - pending review-needed events with no matching pass
  - stale insights (no audits/insights-*.md in last 7 days)
  - accumulated proposed skills in .claude/skills/_evolving/
  - new learnings since last taxonomy sweep

Compares detected signals against .claude/manifests/automation-policy.json and
writes candidates to .claude/context/automation-intents.json.

Usage:
  python3 scripts/harness/automation_planner.py scan     # write intents
  python3 scripts/harness/automation_planner.py list     # show current
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
POLICY = REPO_ROOT / ".claude" / "manifests" / "automation-policy.json"
INTENTS = REPO_ROOT / ".claude" / "context" / "automation-intents.json"


def _now_utc() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def _parse_ts(s: str) -> dt.datetime | None:
    try:
        return dt.datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=dt.timezone.utc)
    except Exception:
        return None


def _load_policy() -> dict:
    if not POLICY.exists():
        return {}
    try:
        return json.loads(POLICY.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def signal_pending_review() -> bool:
    log = REPO_ROOT / ".claude" / "events.jsonl"
    if not log.exists():
        return False
    needed: set[tuple[str, str]] = set()
    passed: set[tuple[str, str]] = set()
    try:
        for line in log.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                e = json.loads(line)
            except json.JSONDecodeError:
                continue
            if e.get("gate") != "02":
                continue
            outcome = e.get("outcome", "")
            key = (e.get("file", ""), e.get("ts", ""))
            if outcome == "review-needed":
                needed.add(key)
            elif outcome == "pass":
                # pass ts != review-needed ts, but `detail.review_needed_ts` may match
                detail = e.get("detail") or {}
                rt = detail.get("review_needed_ts", "")
                f = detail.get("reviewed_file") or e.get("file", "")
                if rt:
                    passed.add((f, rt))
    except OSError:
        return False
    return bool(needed - passed)


def signal_stale_insights(days: int = 7) -> bool:
    audits = REPO_ROOT / ".claude" / "audits"
    if not audits.exists():
        return True
    cutoff = _now_utc() - dt.timedelta(days=days)
    for p in audits.glob("insights-*.md"):
        try:
            mtime = dt.datetime.fromtimestamp(p.stat().st_mtime, tz=dt.timezone.utc)
        except OSError:
            continue
        if mtime >= cutoff:
            return False
    return True


def signal_proposed_skills() -> bool:
    evolving = REPO_ROOT / ".claude" / "skills" / "_evolving"
    if not evolving.exists():
        return False
    return any(p.is_file() or p.is_dir() for p in evolving.iterdir() if p.name != "_")


def signal_learnings_grew(min_new: int = 5) -> bool:
    log = REPO_ROOT / ".claude" / "learnings.jsonl"
    last_sweep = REPO_ROOT / ".claude" / "audits" / "taxonomy-proposals.md"
    if not log.exists():
        return False
    if not last_sweep.exists():
        return True
    try:
        sweep_mtime = dt.datetime.fromtimestamp(
            last_sweep.stat().st_mtime, tz=dt.timezone.utc)
    except OSError:
        return True
    new_count = 0
    try:
        for line in log.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                e = json.loads(line)
            except json.JSONDecodeError:
                continue
            ts = _parse_ts(e.get("ts", "") or "")
            if ts and ts > sweep_mtime:
                new_count += 1
    except OSError:
        return False
    return new_count >= min_new


def scan() -> int:
    policy = _load_policy()
    loops = (policy.get("recommended_loops") or {})
    signal_map = {
        "pending_review_followup": signal_pending_review(),
        "harness_evolution_sweep": signal_stale_insights(),
        "proposed_skill_triage": signal_proposed_skills(),
        "learnings_taxonomy_review": signal_learnings_grew(),
    }
    active: list[dict] = []
    for name, fired in signal_map.items():
        if not fired:
            continue
        loop = loops.get(name, {})
        active.append({
            "name": name,
            "kind": loop.get("kind", "heartbeat"),
            "destination": "thread",
            "cadence_hint": loop.get("cadence_hint", "next-working-block"),
            "trigger": loop.get("trigger", ""),
            "expected_output": loop.get("expected_output", ""),
            "skip_condition": loop.get("skip_condition", ""),
            "evidence": loop.get("evidence", ""),
            "proposed_at": _now_utc().strftime("%Y-%m-%dT%H:%M:%SZ"),
        })

    INTENTS.parent.mkdir(parents=True, exist_ok=True)
    INTENTS.write_text(json.dumps({"intents": active}, indent=2, ensure_ascii=False) + "\n",
                       encoding="utf-8")

    if not active:
        print("  (no automation signals detected)")
        return 0

    print(f"  {len(active)} automation intent(s) proposed:")
    for i in active:
        print(f"  - {i['name']:<32} ({i['kind']}, {i['cadence_hint']})")
        print(f"      trigger: {i['trigger']}")
    print(f"\n  Written to {INTENTS.relative_to(REPO_ROOT)}")
    return 0


def list_intents() -> int:
    if not INTENTS.exists():
        print("  (no intents recorded — run `scan` first)")
        return 0
    data = json.loads(INTENTS.read_text(encoding="utf-8"))
    intents = data.get("intents", [])
    if not intents:
        print("  (no active intents)")
        return 0
    for i in intents:
        print(f"  {i['name']:<32} {i.get('kind'):<12} {i.get('cadence_hint')}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=("scan", "list"))
    args = ap.parse_args()
    if args.cmd == "scan":
        return scan()
    if args.cmd == "list":
        return list_intents()
    return 2


if __name__ == "__main__":
    sys.exit(main())
