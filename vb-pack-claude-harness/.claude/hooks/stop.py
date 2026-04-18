#!/usr/bin/env python3
"""
stop.py — Session-end hook. Runs:
  1. scripts/harness/rotate_logs.py  (segmented append-only rotation)
  2. scripts/harness/meta_supervisor.py  (T1-T6 trigger evaluation)
  3. Layer 4 insights_engine snapshot (weekly/monthly rollup)
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import emit_continue, load_event, resolve_repo_root

# Circuit breaker wiring
import sys as _sys
from pathlib import Path as _P
_sys.path.insert(0, str(_P(__file__).parent.parent.parent / 'scripts' / 'harness'))
try:
    from hook_health import circuit_check as _circuit_check, record_success as _rec_ok, record_failure as _rec_fail  # type: ignore
except Exception:
    _circuit_check = None
    _rec_ok = _rec_fail = None


def _main_impl() -> None:
    event = load_event()
    repo_root = resolve_repo_root(event.get("cwd") if event else None)

    # 1. Rotate logs if thresholds exceeded
    rotate = repo_root / "scripts" / "harness" / "rotate_logs.py"
    if rotate.exists():
        try:
            subprocess.run(["python3", str(rotate)], cwd=str(repo_root),
                           capture_output=True, timeout=15)
        except Exception:
            pass

    # 2. Meta-supervisor trigger check
    supervisor = repo_root / "scripts" / "harness" / "meta_supervisor.py"
    if supervisor.exists():
        try:
            subprocess.run(["python3", str(supervisor)], cwd=str(repo_root),
                           capture_output=True, timeout=20)
        except Exception:
            pass

    # 3. Layer 4: insights_engine rollup (if 7 days elapsed since last)
    insights = repo_root / "scripts" / "harness" / "insights_engine.py"
    if insights.exists():
        try:
            subprocess.run(["python3", str(insights), "--maybe-rollup"],
                           cwd=str(repo_root), capture_output=True, timeout=30)
        except Exception:
            pass

    emit_continue(event_name="Stop")



def main() -> None:
    _HOOK = "stop"
    if _circuit_check is not None:
        _disabled, _reason = _circuit_check(_HOOK)
        if _disabled:
            from common import emit_continue
            emit_continue(system_message=_reason, event_name="")
    try:
        _main_impl()
        if _rec_ok is not None:
            _rec_ok(_HOOK)
    except SystemExit as _se:
        # Any hook that deliberately exits (emit_continue / emit_block) is
        # NOT a failure — emit_block is expected behavior for Pre-hooks.
        if _rec_ok is not None:
            _rec_ok(_HOOK)
        raise
    except Exception as _exc:
        if _rec_fail is not None:
            _rec_fail(_HOOK, reason=str(_exc))
        raise


if __name__ == "__main__":
    main()
