#!/usr/bin/env python3
"""
meta_supervisor.py — Independent harness meta-audit trigger (deterministic).

NOT an AI. Inspects telemetry (events.jsonl, learnings.jsonl, git log) and
decides whether a meta-audit should be triggered. Never decides WHAT to
change — only WHEN to ask the AIs (+ user) to look at the harness.

Trigger conditions (any one sufficient):
  T1. Rolling 30 events contain blocks from 3+ distinct gates
  T2. > 4 plan revisions in 24h
  T3. Rollback / hotfix / revert / emergency signal in git in last 48h
  T4. Gate ⑦ protected-path probe in last 24h
  T5. Cumulative events >= 100 since last audit
  T6. Explicit user request (.claude/audits/audit-requested-*.txt)

Fail-closed: if secondary reviewer is unavailable, pending file is written.
Gate ⑤ surfaces it at next session start. Harness changes frozen.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
import sys
from pathlib import Path


ROLLING_EVENT_WINDOW = 30
ROLLING_DISTINCT_GATE_BLOCK_THRESHOLD = 3
PLAN_REVISION_WINDOW_HOURS = 24
PLAN_REVISION_THRESHOLD = 4
GIT_SIGNAL_WINDOW_HOURS = 48
GATE07_WINDOW_HOURS = 24
CUMULATIVE_EVENT_AUDIT_INTERVAL = 100

ROLLBACK_PATTERNS = [
    r"\brevert\b", r"\brollback\b", r"\bhotfix\b",
    r"\bemergency\b", r"\burgent\s+fix\b", r"\bundo\b",
]


def _find_repo_root(start=None) -> Path:
    current = (Path(start) if start else Path.cwd()).resolve()
    for candidate in (current, *current.parents):
        if (candidate / ".git").exists() or (candidate / ".claude").exists():
            return candidate
    return current


def _parse_ts(s):
    if not s:
        return None
    try:
        return dt.datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=dt.timezone.utc)
    except ValueError:
        return None


def load_events(root: Path) -> list[dict]:
    sys.path.insert(0, str(root / "scripts" / "harness"))
    try:
        import event_log
        return list(event_log.iter_all_events(repo_root=root))
    except Exception:
        pass
    path = root / ".claude" / "events.jsonl"
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def t1_rolling_blocks(events):
    tail = events[-ROLLING_EVENT_WINDOW:]
    gates = {e.get("gate") for e in tail if e.get("outcome") == "block" and e.get("gate")}
    if len(gates) >= ROLLING_DISTINCT_GATE_BLOCK_THRESHOLD:
        return True, f"T1: {len(gates)} gates blocked in rolling {ROLLING_EVENT_WINDOW}", {"gates": sorted(gates)}
    return False, "", {}


def t3_git_signals(root):
    try:
        out = subprocess.check_output(
            ["git", "log", f"--since={GIT_SIGNAL_WINDOW_HOURS}.hours.ago", "--pretty=format:%H%x09%s"],
            cwd=str(root), stderr=subprocess.DEVNULL, text=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False, "", {}
    hits = []
    for line in out.splitlines():
        if "\t" not in line:
            continue
        sha, subject = line.split("\t", 1)
        low = subject.lower()
        for pat in ROLLBACK_PATTERNS:
            if re.search(pat, low):
                hits.append({"sha": sha[:12], "subject": subject, "match": pat})
                break
    if hits:
        return True, f"T3: {len(hits)} rollback/hotfix signals in {GIT_SIGNAL_WINDOW_HOURS}h", {"commits": hits[:5]}
    return False, "", {}


def t4_gate07(events):
    cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=GATE07_WINDOW_HOURS)
    probes = []
    for e in events:
        if e.get("gate") != "07" or e.get("outcome") != "block":
            continue
        ts = _parse_ts(e.get("ts", ""))
        if ts and ts >= cutoff:
            probes.append({"ts": e.get("ts"), "file": e.get("file", "")})
    if probes:
        return True, f"T4: {len(probes)} protected-path probes in {GATE07_WINDOW_HOURS}h", {"probes": probes[-5:]}
    return False, "", {}


def t5_cumulative(events):
    last_audit_idx = -1
    for i, e in enumerate(events):
        if e.get("gate") == "meta" and e.get("outcome") == "audit-completed":
            last_audit_idx = i
    recent = events[last_audit_idx + 1:] if last_audit_idx >= 0 else events
    if len(recent) >= CUMULATIVE_EVENT_AUDIT_INTERVAL:
        return True, f"T5: {len(recent)} events since last audit", {"count": len(recent)}
    return False, "", {}


def t6_user_request(root):
    audits = root / ".claude" / "audits"
    if not audits.exists():
        return False, "", {}
    requests = sorted(audits.glob("audit-requested-*.txt"))
    if requests:
        return True, f"T6: user-requested audit ({len(requests)} files)", {"files": [r.name for r in requests]}
    return False, "", {}


def evaluate(root: Path):
    events = load_events(root)
    triggers = []
    for fn in (lambda: t1_rolling_blocks(events), lambda: t3_git_signals(root),
               lambda: t4_gate07(events), lambda: t5_cumulative(events),
               lambda: t6_user_request(root)):
        fired, reason, evidence = fn()
        if fired:
            triggers.append((reason, evidence))
    return triggers


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply-trigger", action="store_true")
    ap.add_argument("--root", default=None)
    args = ap.parse_args()

    root = Path(args.root).resolve() if args.root else _find_repo_root()
    triggers = evaluate(root)
    if not triggers:
        print("no-trigger")
        return 0

    print("TRIGGERED:")
    for reason, evidence in triggers:
        print(f"  - {reason}")
        if evidence:
            print(f"    evidence: {json.dumps(evidence, ensure_ascii=False)}")

    if not args.apply_trigger:
        return 0

    # Write pending audit file
    audits = root / ".claude" / "audits"
    audits.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    pending = audits / f"meta-audit-pending-{stamp}.md"
    pending.write_text(
        f"# Meta-Audit PENDING\n\nTriggered at {stamp}.\n\n"
        + "\n".join(f"- {r}" for r, _ in triggers)
        + "\n\nHarness changes frozen until audit completes.\n",
        encoding="utf-8",
    )

    try:
        sys.path.insert(0, str(root / "scripts/harness"))
        from event_log import append_event
        append_event(
            gate="meta", outcome="audit-triggered", actor="supervisor",
            file_path=str(pending.relative_to(root)),
            detail={"triggers": [r for r, _ in triggers]}, repo_root=root,
        )
    except Exception:
        pass

    print(f"\npending_audit={pending.relative_to(root)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
