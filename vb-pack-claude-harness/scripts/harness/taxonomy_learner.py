#!/usr/bin/env python3
"""
taxonomy_learner.py — Layer 4: FAILURE_TAXONOMY self-growth.

Collects learnings.jsonl entries with context.pattern_validated=false,
clusters similar unknown patterns, and when a cluster has ≥3 entries
proposes a new vocabulary term to `.claude/audits/taxonomy-proposals.md`.

Exported:
  scan_unknowns(threshold=3) → list[cluster]
  write_proposal(clusters) → proposal file

User approves by editing scripts/harness/learning_log.py FAILURE_TAXONOMY
manually (or via slash command /approve-taxonomy <slug>).

TODO(v1):
  - similarity clustering (simhash / LLM-based)
  - near-duplicate detection against existing vocabulary
"""

from __future__ import annotations

import datetime as dt
import sys
from collections import Counter
from pathlib import Path


def _find_root(start=None) -> Path:
    current = (Path(start) if start else Path.cwd()).resolve()
    for candidate in (current, *current.parents):
        if (candidate / ".git").exists() or (candidate / ".claude").exists():
            return candidate
    return current


def scan_unknowns(repo_root: Path | None = None, threshold: int = 3) -> list[dict]:
    root = repo_root or _find_root()
    sys.path.insert(0, str(root / "scripts" / "harness"))
    try:
        import learning_log
    except Exception:
        return []
    entries = learning_log.load_recent(limit=1000, repo_root=root)
    counter: Counter = Counter()
    examples: dict[str, list[dict]] = {}
    for e in entries:
        ctx = e.get("context", {}) or {}
        if not ctx.get("pattern_validated") is False:
            continue
        pat = e.get("pattern", "")
        if not pat:
            continue
        counter[pat] += 1
        examples.setdefault(pat, []).append(e)

    clusters = []
    for pat, count in counter.items():
        if count >= threshold:
            clusters.append({
                "slug": pat, "count": count,
                "examples": [ex.get("ts") for ex in examples[pat][:5]],
            })
    return clusters


def write_proposal(clusters: list[dict], repo_root: Path | None = None) -> Path:
    root = repo_root or _find_root()
    audits = root / ".claude" / "audits"
    audits.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = audits / f"taxonomy-proposals-{stamp}.md"
    body = [
        "# FAILURE_TAXONOMY growth proposal",
        "",
        f"Generated: {stamp}",
        "",
        "## Candidates (unknown patterns accumulated ≥ 3 times)",
        "",
    ]
    for c in clusters:
        body.append(f"- **{c['slug']}** — {c['count']} occurrences")
        for ex in c["examples"]:
            body.append(f"    - ts: {ex}")
        body.append("")
    body.append("## How to approve")
    body.append("")
    body.append(
        "Add the slug to `FAILURE_TAXONOMY` frozenset in "
        "`scripts/harness/learning_log.py`, commit the change (Gate ⑦ will "
        "require user-approved edit)."
    )
    out.write_text("\n".join(body) + "\n", encoding="utf-8")
    return out


def main() -> int:
    clusters = scan_unknowns()
    if not clusters:
        print("no proposals")
        return 0
    path = write_proposal(clusters)
    print(f"proposal written: {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
