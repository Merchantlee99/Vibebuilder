#!/usr/bin/env python3
"""
risk_policy.py — Computes effective tier from runtime + change signals.

Layer 2 policy. Consumed by hooks/pre_tool_use.py and gate-specific logic.

Exported API:
  effective_tier(runtime, size_result) → 'trivial' | 'normal' | 'high-risk'
  high_risk_reasons(file_path, content) → list[str]
  minimum_tier_from_risk_signals(reasons) → tier

TODO(v1):
  - cross-file impact scoring
  - Layer 4: learning-based tier tuning (insights_engine proposals)
"""

from __future__ import annotations

import re
from typing import Any


HIGH_RISK_PATH_PATTERNS = [
    (r"(^|/)migrations/", "path:migration"),
    (r"(^|/)auth/", "path:auth"),
    (r"(^|/)security/", "path:security"),
    (r"(^|/)payment/|(^|/)billing/", "path:finance"),
    (r"(^|/)\.github/workflows/", "path:ci-config"),
    (r"(^|/)Dockerfile(\.|$)", "path:container"),
    (r"(^|/)k8s/|(^|/)terraform/|(^|/)infra/", "path:infra"),
]

HIGH_RISK_CONTENT_MARKERS = [
    ("secret", "content:secret"),
    ("credential", "content:credential"),
    ("password", "content:password"),
    ("api key", "content:api-key"),
    ("public api", "content:public-api"),
    ("schema migration", "content:schema-migration"),
]


def high_risk_reasons(file_path: str, content: str = "") -> list[str]:
    reasons: list[str] = []
    path = (file_path or "").replace("\\", "/")
    for pat, tag in HIGH_RISK_PATH_PATTERNS:
        if re.search(pat, path, re.IGNORECASE):
            reasons.append(tag)
    blob = (content or "").lower()
    for marker, tag in HIGH_RISK_CONTENT_MARKERS:
        if marker in blob:
            reasons.append(tag)
    return reasons


def minimum_tier_from_risk_signals(reasons: list[str]) -> str:
    if reasons:
        return "high-risk"
    return "normal"


def effective_tier(runtime: dict[str, Any], size_result: dict[str, Any]) -> str:
    """Resolve the final tier by combining:
       - runtime.json → policy.minimum_tier
       - size_check tier
       - runtime.json → policy.high_risk_reasons
    """
    tier_rank = {"trivial": 0, "normal": 1, "high-risk": 2}
    candidates = [
        size_result.get("tier", "normal"),
        (runtime.get("policy") or {}).get("minimum_tier", "normal"),
    ]
    reasons = (runtime.get("policy") or {}).get("high_risk_reasons", [])
    if reasons:
        candidates.append("high-risk")
    rank = max(tier_rank.get(c, 1) for c in candidates)
    for name, r in tier_rank.items():
        if r == rank:
            return name
    return "normal"
