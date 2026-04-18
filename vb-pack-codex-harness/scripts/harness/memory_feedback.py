#!/usr/bin/env python3
"""Hermes-inspired learning-to-action feedback loop utilities."""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import activity_bridge
    import event_log
    import learning_log
    from manifest_loader import load as load_manifest
else:  # pragma: no cover - package import path
    from . import activity_bridge, event_log, learning_log
    from .manifest_loader import load as load_manifest


WORD_RE = re.compile(r"[A-Za-z가-힣][\w-]{2,}")
FAILURE_HINTS = {
    "blocked": "check the blocking condition and narrow scope before retrying",
    "review-fail": "address the cited review findings before continuing",
    "test-fail": "fix the failing validation path before continuing",
    "ownership-conflict": "split or reassign write scopes before parallel work",
}


def _tokenize(text: str) -> set[str]:
    return {match.group(0).lower() for match in WORD_RE.finditer(text or "")}


def evolution_policy(root: Path) -> dict:
    path = root / ".codex" / "manifests" / "evolution-policy.yaml"
    if not path.exists():
        return {}
    return load_manifest(path)


def prefetch(query: str, top_k: int, root: Path) -> str:
    entries = learning_log.load_recent(limit=200, root=root)
    if not entries:
        return ""
    q_tokens = _tokenize(query)
    scored: list[tuple[int, dict]] = []
    for entry in entries:
        blob = " ".join(
            [
                str(entry.get("pattern", "")),
                str(entry.get("mistake", "")),
                str(entry.get("fix", "")),
            ]
        )
        overlap = len(q_tokens & _tokenize(blob))
        if overlap > 0:
            scored.append((overlap, entry))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    chosen = [entry for _, entry in scored[:top_k]]
    return learning_log.format_for_prompt(chosen)


def sync_from_events(limit: int, root: Path) -> int:
    activity_bridge.sync(root)
    recent = list(event_log.iter_events(root))[-limit:]
    existing = {
        (entry.get("context") or {}).get("auto_sig", "")
        for entry in learning_log.load_recent(limit=500, root=root)
    }
    created = 0
    for item in recent:
        kind = str(item.get("kind", ""))
        summary = str(item.get("summary", ""))
        if kind not in FAILURE_HINTS and "block" not in summary.lower() and "fail" not in summary.lower():
            continue
        signature = hashlib.sha1(f"{kind}|{summary}|{item.get('files', [])}".encode("utf-8")).hexdigest()[:16]
        if signature in existing:
            continue
        existing.add(signature)
        pattern = kind or "observed-failure"
        fix = FAILURE_HINTS.get(kind, "inspect the event detail, then document the fix before retrying")
        learning_log.append_learning(
            pattern=pattern,
            mistake=summary or kind,
            fix=fix,
            actor=str(item.get("actor", "system")),
            context={
                "auto_sig": signature,
                "source_event": item,
            },
            root=root,
        )
        created += 1
    return created


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)

    prefetch_cmd = sub.add_parser("prefetch")
    prefetch_cmd.add_argument("query")
    prefetch_cmd.add_argument("--top", type=int, default=None)

    sync_cmd = sub.add_parser("sync-from-events")
    sync_cmd.add_argument("--limit", type=int, default=None)

    args = parser.parse_args()
    root = event_log.repo_root()
    policy = evolution_policy(root)

    if args.cmd == "prefetch":
        default_top = int(policy.get("prefetch", {}).get("top_k", 5) or 5)
        print(prefetch(args.query, args.top or default_top, root))
        return 0

    default_limit = int(policy.get("sync_from_events", {}).get("default_limit", 50) or 50)
    created = sync_from_events(args.limit or default_limit, root)
    print(created)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
