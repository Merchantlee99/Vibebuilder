#!/usr/bin/env python3
"""Generate a lightweight insights report from telemetry and proposed skills."""

from __future__ import annotations

import argparse
import collections
import time
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import activity_bridge
    import event_log
    import learning_log
else:  # pragma: no cover - package import path
    from . import activity_bridge, event_log, learning_log


def generate(root: Path) -> Path:
    activity_bridge.sync(root)
    events = list(event_log.iter_events(root) or [])
    learnings = learning_log.load_recent(limit=1000, root=root)
    event_kinds = collections.Counter(str(item.get("kind", "")) for item in events if item.get("kind"))
    patterns = collections.Counter(str(item.get("pattern", "")) for item in learnings if item.get("pattern"))
    proposed_skills = sorted(
        path
        for path in (root / ".codex" / "skills" / "_proposed").glob("*.md")
        if path.name.lower() != "readme.md"
    )

    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    out_path = root / ".codex" / "audits" / f"insights-{stamp}.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Harness Insights",
        "",
        f"Generated: {stamp}",
        "",
        "## Event Kinds",
        "",
    ]
    if event_kinds:
        lines.extend(f"- {kind}: {count}" for kind, count in event_kinds.most_common())
    else:
        lines.append("- no events yet")
    lines.extend(["", "## Learning Patterns", ""])
    if patterns:
        lines.extend(f"- {pattern}: {count}" for pattern, count in patterns.most_common(10))
    else:
        lines.append("- no learnings yet")
    lines.extend(["", "## Proposed Skills", ""])
    if proposed_skills:
        lines.extend(f"- {path.name}" for path in proposed_skills)
    else:
        lines.append("- none")
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out_path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.parse_args()
    root = event_log.repo_root()
    path = generate(root)
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
