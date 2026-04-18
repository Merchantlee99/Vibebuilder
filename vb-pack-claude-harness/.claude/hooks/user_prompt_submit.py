#!/usr/bin/env python3
"""
user_prompt_submit.py — Layer 4 memory prefetch trigger.

On each user prompt submission:
  1. Invoke memory_manager.prefetch_context(user_message) to identify
     top-5 related learnings from learnings.jsonl.
  2. Inject as additionalContext so Claude sees relevant past experience.
  3. Also check if any `meta-audit-pending-*.md` exists — if so, surface
     as a warning.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import (
    emit_continue, load_event, resolve_repo_root, ensure_harness_importable,
)# Circuit breaker wiring
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
    user_message = event.get("prompt", "") or ""

    additional_context_parts: list[str] = []

    # Layer 4: memory prefetch
    ensure_harness_importable(repo_root)
    try:
        import memory_manager  # type: ignore
        context = memory_manager.prefetch_context(
            user_message=user_message, repo_root=repo_root, top_k=5,
        )
        if context:
            additional_context_parts.append("## Relevant past experience (top-5 from learnings.jsonl)\n")
            additional_context_parts.append(context)
    except Exception:
        pass

    # Meta-audit pending warning
    audits_dir = repo_root / ".claude" / "audits"
    if audits_dir.exists():
        pending = sorted(audits_dir.glob("meta-audit-pending-*.md"))
        if pending:
            additional_context_parts.append(
                f"\n## Meta-audit pending: `{pending[-1].name}`\n"
                f"Harness-level changes are frozen until resolved.\n"
            )

    emit_continue(
        additional_context="\n".join(additional_context_parts) if additional_context_parts else "",
        event_name="UserPromptSubmit",
    )



def main() -> None:
    _HOOK = "user_prompt_submit"
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
