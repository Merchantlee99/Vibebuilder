#!/usr/bin/env python3
"""Recommend local, worktree, or cloud mode from paths and role."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


HIGH_RISK_PATTERNS = [
    r"(^|/)migrations?/",
    r"(^|/)infra/",
    r"(^|/)ops/",
    r"(^|/)security/",
    r"(^|/)auth/",
    r"(^|/)billing/",
    r"(^|/)payment/",
    r"(^|/)\.github/workflows/",
    r"(^|/)terraform/",
    r"(^|/)k8s/",
    r"(^|/)Dockerfile(\.|$)",
]

DOC_PATTERNS = [
    r"(^|/)docs?/",
    r"(^|/)plans?/",
    r"\.md$",
]

COMPLEX_MARKERS = [
    "refactor",
    "migration",
    "auth",
    "payment",
    "security",
    "concurrency",
    "cache",
    "state",
]


def classify(paths: list[str], role: str, clean_room: bool) -> dict[str, object]:
    lowered = [p.replace("\\", "/") for p in paths]
    reasons: list[str] = []
    tier = "trivial"
    complexity = "simple"
    mode = "local"

    file_count = len(lowered)
    if file_count > 1:
        tier = "normal"
        reasons.append("multiple paths are involved")

    for path in lowered:
        if any(re.search(pattern, path, re.IGNORECASE) for pattern in HIGH_RISK_PATTERNS):
            tier = "high-risk"
            mode = "worktree"
            reasons.append(f"high-risk path: {path}")
        if any(re.search(pattern, path, re.IGNORECASE) for pattern in DOC_PATTERNS):
            reasons.append(f"doc-friendly path: {path}")
        if any(marker in path.lower() for marker in COMPLEX_MARKERS):
            complexity = "complex"
            reasons.append(f"complex marker in path: {path}")

    if role == "worker":
        mode = "worktree" if tier != "trivial" or file_count > 1 else "local"
        reasons.append("worker role defaults to worktree for non-trivial edits")
    elif role == "reviewer":
        mode = "cloud" if clean_room else "local"
        reasons.append("reviewer favors isolated read-heavy validation")
    elif clean_room:
        mode = "cloud"
        reasons.append("clean-room flag requested")

    if file_count == 0:
        reasons.append("no paths provided, defaulting to local orchestration")

    return {
        "mode": mode,
        "tier": tier,
        "complexity": complexity,
        "role": role,
        "paths": lowered,
        "reasons": reasons,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--role", choices=["orchestrator", "worker", "reviewer"], default="orchestrator")
    parser.add_argument("--clean-room", action="store_true")
    parser.add_argument("paths", nargs="*")
    args = parser.parse_args()

    result = classify(args.paths, args.role, args.clean_room)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
