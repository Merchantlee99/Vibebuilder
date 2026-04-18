#!/usr/bin/env python3
"""
oversight_policy.py — Layer 2: retry budget + review freshness policy.

Exported:
  should_escalate_retry(runtime) → bool
  next_retry_state(runtime, reason) → updated runtime dict
  reset_retry_state(runtime) → updated runtime dict
  review_metadata_is_fresh(event, max_age_minutes=30) → bool

TODO(v1):
  - Layer 4 integration: learning-based retry budget tuning
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone


def should_escalate_retry(runtime: dict) -> bool:
    retry = (runtime.get("execution", {}) or {}).get("retry", {}) or {}
    count = int(retry.get("count", 0) or 0)
    budget = int((runtime.get("limits", {}) or {}).get("retry_budget", 3) or 3)
    return count >= budget


def next_retry_state(runtime: dict, reason: str) -> dict:
    rt = dict(runtime)
    exec_ = dict(rt.get("execution", {}) or {})
    retry = dict(exec_.get("retry", {}) or {"count": 0, "reasons": []})
    retry["count"] = int(retry.get("count", 0)) + 1
    reasons = list(retry.get("reasons", []))
    reasons.append(reason)
    retry["reasons"] = reasons[-20:]
    exec_["retry"] = retry
    rt["execution"] = exec_
    return rt


def reset_retry_state(runtime: dict) -> dict:
    rt = dict(runtime)
    exec_ = dict(rt.get("execution", {}) or {})
    exec_["retry"] = {"count": 0, "reasons": []}
    rt["execution"] = exec_
    return rt


def review_metadata_is_fresh(event: dict, max_age_minutes: int = 30) -> bool:
    ts = event.get("ts", "")
    try:
        when = datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except Exception:
        return False
    return datetime.now(timezone.utc) - when <= timedelta(minutes=max_age_minutes)
