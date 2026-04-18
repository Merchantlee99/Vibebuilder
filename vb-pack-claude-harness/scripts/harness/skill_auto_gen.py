#!/usr/bin/env python3
"""
skill_auto_gen.py — Layer 4: autonomous skill draft generation.

When the same task-type pattern is observed ≥ 3 times in events.jsonl,
propose a new SKILL.md draft under .claude/skills/_evolving/<slug>/.

Exported:
  scan_for_patterns(threshold=3) → list[pattern]
  propose_skill(pattern) → .claude/skills/_evolving/<slug>/SKILL.md

User must explicitly approve (move from _evolving/ with a marker note)
before the skill becomes active.

TODO(v1):
  - task-type clustering from events.jsonl (currently placeholder)
  - trajectory analysis for skill body
  - user approval UI (slash command /approve-skill <slug>)
"""

from __future__ import annotations

import sys
from pathlib import Path


def _find_root(start=None) -> Path:
    current = (Path(start) if start else Path.cwd()).resolve()
    for candidate in (current, *current.parents):
        if (candidate / ".git").exists() or (candidate / ".claude").exists():
            return candidate
    return current


def scan_for_patterns(repo_root: Path | None = None, threshold: int = 3) -> list[dict]:
    """Cluster events.jsonl by (gate, outcome, file_basename) and propose
    skills for patterns seen ≥ threshold times.

    Returns list of {"slug", "count", "examples": [ts]}.

    Clustering heuristic:
      - For gate ∈ {02, 06} outcome=block: groups by reason + file basename
      - For gate=03 outcome=info: skips (already learnings)
      - For gate=04 outcome=block: tests repeatedly failing → skill candidate
      - For review-needed w/ same tier+complexity+file_pattern ≥3: skill candidate

    Rejects slugs that already exist in _manual/ or have REJECTED.md in
    _evolving/. Does not duplicate across runs (idempotent: uses exist check).
    """
    from collections import Counter
    root = repo_root or _find_root()
    sys.path.insert(0, str(root / "scripts" / "harness"))
    try:
        import event_log  # type: ignore
    except Exception:
        return []

    # Existing skills (don't re-propose)
    existing_manual = {p.name for p in (root / ".claude" / "skills" / "_manual").glob("*") if p.is_dir()}
    rejected_evolving = {
        p.parent.name for p in (root / ".claude" / "skills" / "_evolving").rglob("REJECTED.md")
    }
    existing_proposals = {
        p.parent.name for p in (root / ".claude" / "skills" / "_evolving").rglob("SKILL.md")
    }
    skip_slugs = existing_manual | rejected_evolving | existing_proposals

    # Bucket signals
    counter: Counter = Counter()
    examples: dict[str, list[str]] = {}
    for e in event_log.iter_all_events(repo_root=root):
        gate = str(e.get("gate", ""))
        outcome = str(e.get("outcome", ""))
        detail = e.get("detail") or {}
        file_ = e.get("file", "") or ""
        base = Path(file_).stem if file_ else ""

        # Repeated block on same file → "recover-<basename>" skill
        if outcome == "block" and base:
            reason = str(detail.get("reason", ""))[:40].replace(" ", "-").lower()
            slug = f"recover-{base}-{gate}"
            if reason:
                slug += f"-{reason}"
            slug = slug[:60]
            counter[slug] += 1
            examples.setdefault(slug, []).append(e.get("ts", ""))
            continue

        # Repeated gate-04 block (tests failing) on same file
        if gate == "04" and outcome == "block" and base:
            slug = f"fix-tests-{base}"[:60]
            counter[slug] += 1
            examples.setdefault(slug, []).append(e.get("ts", ""))
            continue

        # Repeated review-needed on same (tier, complexity, dir)
        if gate == "02" and outcome == "review-needed":
            tier = detail.get("tier", "")
            complexity = detail.get("complexity", "simple")
            dir_part = "/".join(file_.split("/")[:-1]) if "/" in file_ else "root"
            slug = f"{tier}-{complexity}-{dir_part.replace('/', '-')}"[:60]
            counter[slug] += 1
            examples.setdefault(slug, []).append(e.get("ts", ""))

    # Filter: threshold + not already existing
    out: list[dict] = []
    for slug, count in counter.items():
        if count < threshold:
            continue
        if slug in skip_slugs:
            continue
        out.append({
            "slug": slug, "count": count,
            "examples": examples[slug][:5],
        })
    return out


def propose_skill(pattern: dict, repo_root: Path | None = None) -> Path:
    """Write a draft SKILL.md to _evolving/<slug>/SKILL.md with pattern evidence."""
    root = repo_root or _find_root()
    slug = pattern.get("slug") or "unknown-pattern"
    dest_dir = root / ".claude" / "skills" / "_evolving" / slug
    dest_dir.mkdir(parents=True, exist_ok=True)

    body = (
        f"---\n"
        f"name: {slug}\n"
        f"status: draft-proposed\n"
        f"source: skill_auto_gen.py\n"
        f"evidence: {pattern.get('count', 0)} occurrences\n"
        f"---\n\n"
        f"# {slug}\n\n"
        f"**DRAFT** — auto-generated skill proposal. User approval required.\n\n"
        f"## Pattern\n\n"
        f"This skill would cover the pattern observed {pattern.get('count', 0)} times.\n\n"
        f"## Examples\n\n"
    )
    for ex in pattern.get("examples", [])[:5]:
        body += f"- {ex}\n"
    body += (
        "\n## When to invoke\n\n"
        "(auto-filled from example event contexts — TBD)\n\n"
        "## Steps\n\n"
        "(proposed sequence — TBD)\n\n"
        "## Guardrails\n\n"
        "- Respect Layer 3 gates (especially actor crossover)\n"
        "- Treat this file as draft until user moves out of `_evolving/`\n"
    )
    (dest_dir / "SKILL.md").write_text(body, encoding="utf-8")

    history = dest_dir / "history.jsonl"
    history.touch()

    return dest_dir / "SKILL.md"
