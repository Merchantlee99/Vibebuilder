#!/usr/bin/env python3
"""Generate proposed skills from repeated learning patterns."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import learning_log
    import event_log
    from manifest_loader import load as load_manifest
else:  # pragma: no cover - package import path
    from . import learning_log, event_log
    from .manifest_loader import load as load_manifest


SKILL_DIR = Path(".codex/skills/_proposed")


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug or "untitled-skill"


def evolution_policy(root: Path) -> dict:
    path = root / ".codex" / "manifests" / "evolution-policy.yaml"
    if not path.exists():
        return {}
    return load_manifest(path)


def generate(threshold: int, root: Path) -> list[Path]:
    entries = learning_log.load_recent(limit=500, root=root)
    grouped: dict[str, list[dict]] = {}
    for entry in entries:
        pattern = str(entry.get("pattern", "")).strip()
        if not pattern:
            continue
        grouped.setdefault(pattern, []).append(entry)

    output_dir = root / SKILL_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    created: list[Path] = []
    for pattern, items in grouped.items():
        if len(items) < threshold:
            continue
        path = output_dir / f"{slugify(pattern)}.md"
        if path.exists():
            continue
        recent = items[-3:]
        fixes = [str(item.get("fix", "")) for item in recent if item.get("fix")]
        mistakes = [str(item.get("mistake", "")) for item in recent if item.get("mistake")]
        lines = [
            f"# Proposed Skill — {pattern}",
            "",
            "## Why This Exists",
            "",
            f"This proposal was generated after `{pattern}` appeared {len(items)} times in the learning log.",
            "",
            "## Trigger",
            "",
            f"- Use when the task shows signs of `{pattern}`.",
            "",
            "## Observed Mistakes",
            "",
        ]
        lines.extend(f"- {mistake}" for mistake in mistakes[:5] or ["- none recorded"])
        lines.extend(
            [
                "",
                "## Suggested Workflow",
                "",
            ]
        )
        lines.extend(f"- {fix}" for fix in fixes[:5] or ["- review the repeated pattern and define a safer default workflow"])
        lines.extend(
            [
                "",
                "## Checks",
                "",
                "- Confirm scope and ownership before acting.",
                "- Confirm validation path before completion.",
                "- Promote only after human review.",
            ]
        )
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        created.append(path)

    if created:
        event_log.append_event(
            kind="skill-proposal",
            actor="system",
            summary=f"generated {len(created)} proposed skills",
            files=[str(path.relative_to(root)) for path in created],
            stage="evolution",
            root=root,
        )
    return created


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--threshold", type=int, default=None)
    args = parser.parse_args()

    root = event_log.repo_root()
    policy = evolution_policy(root)
    threshold = args.threshold
    if threshold is None:
        threshold = int(policy.get("skill_auto_gen", {}).get("threshold", 3) or 3)
    created = generate(threshold, root)
    for path in created:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
