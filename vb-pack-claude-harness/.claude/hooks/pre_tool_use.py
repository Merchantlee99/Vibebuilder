#!/usr/bin/env python3
"""
pre_tool_use.py — Unified Pre-Edit hook. Runs Layer 3 gates ①/⑥/⑦/⑩ in order.

Gate ⑦ (self-protect) first — fast fail on protected paths.
Gate ⑩ (parallel spike) — only if flag + high-risk + complex.
Gate ⑥ (scope) — cumulative size + Bash-bypass signal.
Gate ① (direction check) — normal/high-risk tier requires recent pass event.
Gate ② (Pre mode: unresolved review + latest Gate ④) — implementation below.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import (
    ensure_harness_importable, emit_block, emit_continue, extract_paths,
    extract_tool_input, extract_tool_name, is_protected_path, load_event,
    load_runtime, normalize_repo_path, resolve_repo_root, run_size_check,
    tool_mutates_repo,
)# Circuit breaker wiring
import sys as _sys
from pathlib import Path as _P
_sys.path.insert(0, str(_P(__file__).parent.parent.parent / 'scripts' / 'harness'))
try:
    from hook_health import circuit_check as _circuit_check, record_success as _rec_ok, record_failure as _rec_fail  # type: ignore
except Exception:
    _circuit_check = None
    _rec_ok = _rec_fail = None



def gate_7_selfprotect(repo_root: Path, rel_paths: list[str]) -> None:
    """Exit 2 if any path hits control-plane protection."""
    for rel in rel_paths:
        matched = is_protected_path(rel)
        if matched is not None:
            ensure_harness_importable(repo_root)
            try:
                import event_log  # type: ignore
                event_log.append_event(
                    gate="07", outcome="block", actor="claude", file_path=rel,
                    detail={"reason": "protected control-plane path", "pattern": matched.pattern},
                    repo_root=repo_root,
                )
            except Exception:
                pass
            emit_block(
                f"BLOCKED by Gate ⑦ (harness self-protection).\n\n"
                f"Path: {rel}\n"
                f"Reason: matches protected pattern `{matched.pattern}`\n\n"
                f"This file is part of the harness control plane. AI cannot modify "
                f"it unilaterally. Ask the user explicitly or route via meta-audit."
            )


def gate_10_parallel_spike(repo_root: Path, size: dict) -> None:
    """If .claude/parallel-spike.flag exists AND tier=high-risk AND complexity=complex,
    require both .claude/spikes/<sess>/<target>/{claude,codex}.md before proceeding.
    """
    flag = repo_root / ".claude" / "parallel-spike.flag"
    if not flag.exists():
        return
    if size["tier"] != "high-risk" or size["complexity"] != "complex":
        return
    if not size["file_path"]:
        return

    ensure_harness_importable(repo_root)
    import event_log  # type: ignore

    session_id = event_log._resolve_session_id()
    safe_name = size["file_path"].replace("/", "_").replace(".", "_")
    spike_dir = repo_root / ".claude" / "spikes" / session_id / safe_name
    claude_spike = spike_dir / "claude.md"
    codex_spike = spike_dir / "codex.md"

    if (claude_spike.exists() and codex_spike.exists()
            and claude_spike.stat().st_size > 200 and codex_spike.stat().st_size > 200):
        event_log.append_event(
            gate="10", outcome="pass", actor="claude", file_path=size["file_path"],
            detail={"claude_spike": str(claude_spike), "codex_spike": str(codex_spike),
                    "tier": size["tier"], "complexity": size["complexity"]},
            repo_root=repo_root,
        )
        return

    spike_dir.mkdir(parents=True, exist_ok=True)
    event_log.append_event(
        gate="10", outcome="block", actor="claude", file_path=size["file_path"],
        detail={"reason": "parallel spikes required", "spike_dir": str(spike_dir),
                "tier": size["tier"], "complexity": size["complexity"]},
        repo_root=repo_root,
    )
    emit_block(
        f"BLOCKED by Gate ⑩ (parallel spike required).\n\n"
        f"Target: {size['file_path']}\n"
        f"Tier: {size['tier']}, Complexity: {size['complexity']}\n\n"
        f"Before implementing, create TWO design documents:\n"
        f"  1. {claude_spike}\n"
        f"  2. {codex_spike}\n\n"
        f"To cancel: rm {flag}"
    )


def gate_6_scope(repo_root: Path, size: dict, runtime: dict) -> None:
    """Blocks if cumulative LOC/files would exceed approved tier's ceiling."""
    ensure_harness_importable(repo_root)
    import event_log  # type: ignore

    session_id = event_log._resolve_session_id()

    tier_rank = {"trivial": 0, "normal": 1, "high-risk": 2}
    approved_tier = "trivial"
    approved_rank = 0
    cumulative_loc = 0
    files_seen: set[str] = set()

    for e in event_log.iter_all_events(repo_root=repo_root):
        ev_sess = e.get("session") or ""
        if not ev_sess:
            continue
        if ev_sess != session_id:
            continue
        gate = e.get("gate", "")
        outcome = e.get("outcome", "")
        detail = e.get("detail") or {}
        if gate == "01" and outcome == "pass":
            t = str(detail.get("tier", "") or "")
            r = tier_rank.get(t, -1)
            if r > approved_rank:
                approved_rank = r
                approved_tier = t
        elif gate == "06" and outcome == "edit-tracked":
            try:
                cumulative_loc += int(detail.get("total_loc", 0) or 0)
            except (TypeError, ValueError):
                pass
            f_ = e.get("file", "")
            if f_:
                files_seen.add(f_)

    projected_loc = cumulative_loc + size["total"]
    projected_files = set(files_seen)
    if size["file_path"]:
        projected_files.add(size["file_path"])

    edit_rank = tier_rank.get(size["tier"], 0)
    if approved_rank == 0:
        ceiling_loc, ceiling_files = 20, 1
    elif approved_rank == 1:
        ceiling_loc, ceiling_files = 100, 5
    else:
        ceiling_loc, ceiling_files = 10**9, 10**9

    if edit_rank == 2 and approved_rank < 2:
        event_log.append_event(
            gate="06", outcome="block", actor="claude", file_path=size["file_path"],
            detail={"reason": "content-or-path-high-risk",
                    "approved_tier": approved_tier, "tier": size["tier"]},
            repo_root=repo_root,
        )
        emit_block(
            f"BLOCKED by Gate ⑥ (scope check).\n"
            f"Edit classifies as high-risk but approved tier is {approved_tier}.\n"
            f"Re-run Gate ① at high-risk tier first."
        )

    if projected_loc > ceiling_loc or len(projected_files) > ceiling_files:
        event_log.append_event(
            gate="06", outcome="block", actor="claude", file_path=size["file_path"],
            detail={"reason": "size-exceeded", "approved_tier": approved_tier,
                    "cumulative_loc": cumulative_loc, "projected_loc": projected_loc,
                    "projected_files": len(projected_files)},
            repo_root=repo_root,
        )
        next_tier = "normal" if approved_tier == "trivial" else "high-risk"
        emit_block(
            f"BLOCKED by Gate ⑥ (scope check).\n\n"
            f"Approved tier: {approved_tier}\n"
            f"Cumulative: {cumulative_loc} LOC / {len(files_seen)} file(s)\n"
            f"Projected after: {projected_loc} LOC / {len(projected_files)} file(s)\n"
            f"Ceiling: {ceiling_loc} LOC / {ceiling_files} file(s)\n\n"
            f"Re-run Gate ① at {next_tier} tier."
        )


def gate_2_pre(repo_root: Path, size: dict) -> None:
    """Gate ② Pre — the core mutual-redteam enforcement.

    Blocks the next non-trivial edit unless BOTH:
      (a) every prior review-needed event for any file has a matching
          Gate ② pass event with:
            - reviewer_file exists under .claude/reviews/, size >= 800B
            - contains "Verdict:" keyword
            - contains >=2 sealed-prompt structural fingerprints
            - for code reviews: has rollback-trigger evidence
            - contains >=1 structured objection block (File+Issue+Evidence)
            - reviewer actor != author actor (actor crossover, P2-F)
            - pass ts >= review-needed ts (same-second OK, P4-7)
      (b) the most recent Gate ④ event for the SAME file is NOT outcome=block
          (per-file scope, P4-4; >= compare for same-ts pass-after-block, P4-7b)

    Trivial tier always passes.
    """
    if size["tier"] == "trivial":
        return

    ensure_harness_importable(repo_root)
    try:
        import event_log  # type: ignore
    except Exception:
        return

    import re as _re

    session_id = event_log._resolve_session_id()
    reviews_root = (repo_root / ".claude" / "reviews").resolve()

    # -- first pass: collect review-needed per file + actor --
    pending: dict[str, list[tuple[str, str]]] = {}  # file -> [(ts, author_actor)]
    for e in event_log.iter_all_events(repo_root=repo_root):
        if e.get("gate") != "02":
            continue
        ev_sess = e.get("session") or ""
        if not ev_sess or ev_sess != session_id:
            continue
        if e.get("outcome") != "review-needed":
            continue
        file_ = e.get("file", "")
        if not file_:
            continue
        pending.setdefault(file_, []).append(
            (e.get("ts", ""), e.get("actor", ""))
        )

    # -- second pass: match pass events; each valid pass pops the earliest
    #    matching review-needed in its queue --
    for e in event_log.iter_all_events(repo_root=repo_root):
        if e.get("gate") != "02":
            continue
        ev_sess = e.get("session") or ""
        if not ev_sess or ev_sess != session_id:
            continue
        if e.get("outcome") != "pass":
            continue

        detail = e.get("detail") or {}
        reviewer_file = detail.get("reviewer_file", "")
        reviewed_file = detail.get("reviewed_file", "") or e.get("file", "")
        if not reviewer_file or not reviewed_file:
            continue

        # reviewer_file must live under .claude/reviews/
        rpath = repo_root / reviewer_file
        try:
            rpath_resolved = rpath.resolve()
            if (reviews_root not in rpath_resolved.parents
                    and rpath_resolved != reviews_root):
                continue
        except (OSError, RuntimeError):
            continue

        # size >= 800B (P1-C + P4-5)
        if not rpath.exists() or rpath.stat().st_size < 800:
            continue

        try:
            body = rpath.read_text(encoding="utf-8", errors="replace")[:8192]
        except OSError:
            continue

        if "Verdict:" not in body:
            continue

        # >=2 structural fingerprints (P4-5)
        code_fp = ["Severity of worst finding:", "Tests actually exercising"]
        plan_fp = ["Missing citations", "Unstated assumptions"]
        rollback_fp = ["Rollback triggers:", "Rollback recommended:"]
        fp_hits = sum(1 for fp in (code_fp + plan_fp) if fp in body)
        if fp_hits < 2:
            continue

        # code review → rollback evidence required (P3-B)
        rfl = reviewed_file.lower()
        is_code_review = (not rfl.endswith((".md", ".mdx", ".txt", ".rst"))
                          and not any(rfl.startswith(p) for p in (
                              "plans/", "docs/", "specs/", "notes/")))
        if is_code_review and not any(fp in body for fp in rollback_fp):
            continue

        # structured objection block (File/Claim + Issue + Evidence) (P4-5)
        obj_blocks = _re.findall(
            r"^\s*\d+\.\s+(?:Claim:|File:).*?(?=^\s*\d+\.|\Z)",
            body, flags=_re.MULTILINE | _re.DOTALL,
        )
        valid_obj = False
        for blk in obj_blocks:
            hf = "File:" in blk or "Claim:" in blk
            hi = "Issue:" in blk or "Why it is weak:" in blk
            he = ("Evidence:" in blk
                  or "Evidence from the codebase:" in blk)
            if hf and hi and he:
                valid_obj = True
                break
        if not valid_obj:
            continue

        reviewer_actor = e.get("actor", "")
        pass_ts = e.get("ts", "")

        # actor crossover + ts match (earliest pending with need_ts<=pass_ts
        # AND author_actor != reviewer_actor)
        queue = pending.get(reviewed_file, [])
        for i, (need_ts, author_actor) in enumerate(queue):
            if need_ts <= pass_ts and author_actor != reviewer_actor:
                queue.pop(i)
                break

    unresolved = sum(len(v) for v in pending.values())
    last_pending_file = ""
    last_pending_ts = ""
    for f_, rows in pending.items():
        for ts, _author in rows:
            if ts > last_pending_ts:
                last_pending_ts = ts
                last_pending_file = f_

    # -- Gate ④ per-file latest outcome (P4-4 + P4-7b) --
    target_file = size["file_path"]
    gate4_latest: dict[str, tuple[str, str]] = {}  # file -> (ts, outcome)
    for e in event_log.iter_all_events(repo_root=repo_root):
        if e.get("gate") != "04":
            continue
        ev_sess = e.get("session") or ""
        if not ev_sess or ev_sess != session_id:
            continue
        ts = e.get("ts", "")
        f_ = e.get("file", "") or ""
        prev = gate4_latest.get(f_)
        if prev is None or ts >= prev[0]:  # P4-7b: >= for same-ts pass after block
            gate4_latest[f_] = (ts, e.get("outcome", ""))

    latest_for_target = gate4_latest.get(target_file, (None, ""))
    gate4_blocked = latest_for_target[1] == "block"

    if unresolved == 0 and not gate4_blocked:
        return

    # Pure gate-04 failure (no unresolved review, but tests red)
    if unresolved == 0 and gate4_blocked:
        event_log.append_event(
            gate="02", outcome="block", actor="claude", file_path=target_file,
            detail={"tier": size["tier"],
                    "reason": "most recent gate-04 outcome is block",
                    "gate4_file": target_file},
            repo_root=repo_root,
        )
        emit_block(
            f"BLOCKED by Gate ② (P1-A: tests must be green).\n\n"
            f"Attempted: {target_file} ({size['tier']}, {size['total']} LOC)\n"
            f"Most recent Gate ④ outcome for this file: block\n\n"
            f"How to unblock:\n"
            f"  1. Read .claude/test-runs/run-*.log and fix the failing tests\n"
            f"  2. Re-trigger Gate ④ by editing any code file\n"
            f"  3. When Gate ④ emits outcome=pass for {target_file}, this releases\n\n"
            f"False positive? Record manual pass:\n"
            f"  python3 scripts/harness/event_log.py 04 pass user {target_file} "
            f"with a reason detail JSON"
        )

    # Unresolved review(s) — require reviewer pass before next edit
    event_log.append_event(
        gate="02", outcome="block", actor="claude", file_path=target_file,
        detail={"tier": size["tier"], "unresolved": unresolved,
                "pending_file": last_pending_file,
                "reason": "prior review unrecorded or invalid"},
        repo_root=repo_root,
    )
    emit_block(
        f"BLOCKED by Gate ② (mutual review required).\n\n"
        f"Attempted: {target_file} ({size['tier']}, {size['total']} LOC)\n"
        f"Unresolved reviews in this session: {unresolved}\n"
        f"Most recent pending: {last_pending_file}\n\n"
        f"Before starting a NEW non-trivial change, the opposite actor must "
        f"review the prior one.\n\n"
        f"How to unblock:\n"
        f"  1. Invoke reviewer with .claude/sealed-prompts/review-code.md "
        f"(or review-plan.md) on {last_pending_file}.\n"
        f"  2. Reviewer writes .claude/reviews/<ts>.md with sealed-prompt "
        f"structure: Verdict:, Severity of worst finding:, at least one "
        f"File:/Issue:/Evidence: block, and (for code reviews) "
        f"Rollback triggers: section.\n"
        f"  3. Record pass with the REVIEWER actor (must differ from author):\n"
        f"     python3 scripts/harness/event_log.py 02 pass <reviewer-actor> "
        f"{last_pending_file} <<JSON\n"
        f'     {{"reviewer_file":".claude/reviews/<file>.md", '
        f'"summary":"...", "reviewed_file":"{last_pending_file}", '
        f'"verdict":"accept|revise|reject"}}'
    )


def gate_1_direction(repo_root: Path, size: dict) -> None:
    """Block if tier is normal/high-risk AND no recent Gate ① pass in session."""
    if size["tier"] == "trivial":
        return
    ensure_harness_importable(repo_root)
    import event_log  # type: ignore
    from datetime import datetime, timedelta, timezone

    session_id = event_log._resolve_session_id()
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=30)

    def parse_ts(s):
        try:
            return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        except Exception:
            return None

    valid = False
    for e in event_log.iter_all_events(repo_root=repo_root):
        if e.get("gate") != "01" or e.get("outcome") != "pass":
            continue
        ev_sess = e.get("session") or ""
        if not ev_sess or ev_sess != session_id:
            continue
        ts = parse_ts(e.get("ts", ""))
        if ts is None or ts < cutoff:
            continue
        detail = e.get("detail") or {}
        codex_file = detail.get("codex_response_file", "")
        if not codex_file:
            continue
        codex_abs = repo_root / codex_file
        if not codex_abs.exists() or codex_abs.stat().st_size < 50:
            continue
        valid = True
        break

    if valid:
        return

    event_log.append_event(
        gate="01", outcome="block", actor="claude", file_path=size["file_path"],
        detail={"tier": size["tier"], "complexity": size["complexity"],
                "total_loc": size["total"], "reason": "no recent direction-check"},
        repo_root=repo_root,
    )
    emit_block(
        f"BLOCKED by Gate ① (direction check required).\n\n"
        f"Path: {size['file_path']}\n"
        f"Tier: {size['tier']} (total={size['total']} LOC)\n"
        f"Complexity: {size['complexity']}\n\n"
        f"Before a {size['tier']} change, the secondary reviewer must approve direction.\n"
        f"1. Invoke reviewer with .claude/sealed-prompts/direction-check.md\n"
        f"2. They write .claude/direction-checks/<ts>.md\n"
        f"3. Record: python3 scripts/harness/event_log.py 01 pass <reviewer-actor> <file> <<JSON\n"
        f"   {{\"codex_response_file\":\"...\", \"summary\":\"...\", \"tier\":\"{size['tier']}\"}}"
    )


def _main_impl() -> None:
    raw = sys.stdin.read()
    try:
        event = json.loads(raw) if raw else {}
    except json.JSONDecodeError:
        event = {}

    repo_root = resolve_repo_root(event.get("cwd") if event else None)
    tool_name = extract_tool_name(event)

    if not tool_mutates_repo(tool_name):
        emit_continue(event_name="PreToolUse")

    # Normalize paths
    rel_paths: list[str] = []
    for p in extract_paths(event):
        rel = normalize_repo_path(repo_root, p)
        if rel:
            rel_paths.append(rel)

    # Gate ⑦ first (self-protection)
    gate_7_selfprotect(repo_root, rel_paths)

    # size_check → tier + complexity
    size = run_size_check(repo_root, raw)

    if not size["file_path"]:
        emit_continue(event_name="PreToolUse")

    # Gate ⑩ (parallel spike) — opt-in flag
    gate_10_parallel_spike(repo_root, size)

    # Runtime state
    runtime, _ = load_runtime(repo_root)
    if not runtime or runtime.get("_invalid"):
        runtime = {}

    # Gate ⑥ (scope)
    gate_6_scope(repo_root, size, runtime)

    # Gate ① (direction check)
    gate_1_direction(repo_root, size)

    # Gate ② Pre (mutual review + Gate ④ freshness + actor crossover +
    # fingerprint + rollback triggers — all unified enforcement)
    gate_2_pre(repo_root, size)

    emit_continue(event_name="PreToolUse")



def main() -> None:
    _HOOK = "pre_tool_use"
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
