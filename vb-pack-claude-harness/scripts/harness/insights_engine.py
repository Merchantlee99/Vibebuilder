#!/usr/bin/env python3
"""
insights_engine.py — Layer 4: periodic usage pattern analysis.

Inspired by hermes-agent's insights.py. Rolls up events.jsonl + learnings.jsonl
into weekly/monthly summaries:
  - Which gates fire most? What files fail repeatedly?
  - Is tier threshold realistic? (e.g. normal ≤100 LOC actually sees 200+)
  - Which sealed-prompts are most effective (low revise/reject rate)?
  - Which roles are bottleneck (frequent block at same reviewer)?

Writes to .claude/audits/insights-<ts>.md. Sets runtime.json
→ self_evolving.pending_proposals for user review.

CLI:
  python3 scripts/harness/insights_engine.py            # run now if due
  python3 scripts/harness/insights_engine.py --maybe-rollup   # only if 7 days since last
  python3 scripts/harness/insights_engine.py --force    # run unconditionally

TODO(v1):
  - sealed-prompt effectiveness scoring
  - tier threshold auto-tune proposal
  - cost telemetry (token / time estimates)
"""

from __future__ import annotations

import datetime as dt
import json
import sys
from collections import Counter
from pathlib import Path


INTERVAL_DAYS = 7


def _find_root(start=None) -> Path:
    current = (Path(start) if start else Path.cwd()).resolve()
    for candidate in (current, *current.parents):
        if (candidate / ".git").exists() or (candidate / ".claude").exists():
            return candidate
    return current


def _days_since_last_rollup(root: Path) -> int:
    audits = root / ".claude" / "audits"
    if not audits.exists():
        return 999
    files = sorted(audits.glob("insights-*.md"))
    if not files:
        return 999
    last = files[-1]
    age_sec = dt.datetime.now().timestamp() - last.stat().st_mtime
    return int(age_sec // 86400)


def run_rollup(repo_root: Path | None = None) -> Path:
    root = repo_root or _find_root()
    sys.path.insert(0, str(root / "scripts" / "harness"))
    try:
        import event_log
    except Exception:
        raise RuntimeError("event_log unavailable")

    events = list(event_log.iter_all_events(repo_root=root))
    gate_counter: Counter = Counter()
    outcome_counter: Counter = Counter()
    blocks_by_gate: Counter = Counter()
    files_failing: Counter = Counter()

    for e in events:
        gate_counter[e.get("gate", "?")] += 1
        outcome_counter[e.get("outcome", "?")] += 1
        if e.get("outcome") == "block":
            blocks_by_gate[e.get("gate", "?")] += 1
            f_ = e.get("file", "")
            if f_:
                files_failing[f_] += 1

    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = root / ".claude" / "audits" / f"insights-{stamp}.md"
    out.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        "# Harness Insights",
        "",
        f"Generated: {stamp}",
        f"Total events: {len(events)}",
        "",
        "## Gate firing frequency (top 10)",
        "",
    ]
    for gate, count in gate_counter.most_common(10):
        lines.append(f"- gate={gate}: {count}")

    lines.extend(["", "## Outcome distribution (top 10)", ""])
    for outcome, count in outcome_counter.most_common(10):
        lines.append(f"- {outcome}: {count}")

    lines.extend(["", "## Blocks by gate", ""])
    for gate, count in blocks_by_gate.most_common():
        lines.append(f"- gate={gate}: {count} blocks")

    lines.extend(["", "## Files blocked most (top 10)", ""])
    for f_, count in files_failing.most_common(10):
        lines.append(f"- `{f_}`: {count}")

    lines.extend([
        "",
        "## Proposals (if any — user approval required)",
        "",
        "(tier threshold tuning / sealed-prompt aging / skill auto-gen — "
        "none in this skeleton rollup; full implementation in v1)",
        "",
    ])
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--maybe-rollup", action="store_true",
                    help="only run if ≥7 days since last")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    root = _find_root()
    if args.maybe_rollup and not args.force:
        age = _days_since_last_rollup(root)
        if age < INTERVAL_DAYS:
            print(f"skip: last rollup was {age} days ago (< {INTERVAL_DAYS})")
            return 0

    out = run_rollup(root)
    print(f"rollup written: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
