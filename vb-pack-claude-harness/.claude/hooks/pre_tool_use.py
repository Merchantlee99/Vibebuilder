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
import re
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
    from hook_health import circuit_check as _circuit_check, circuit_severity as _circuit_severity, record_success as _rec_ok, record_failure as _rec_fail  # type: ignore
except Exception:
    _circuit_check = None
    _circuit_severity = None
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
    require both .claude/spikes/<sess>/<target>/{design-a,design-b}.md before proceeding.
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
    design_a = spike_dir / "design-a.md"
    design_b = spike_dir / "design-b.md"

    if (design_a.exists() and design_b.exists()
            and design_a.stat().st_size > 200 and design_b.stat().st_size > 200):
        event_log.append_event(
            gate="10", outcome="pass", actor="claude", file_path=size["file_path"],
            detail={"design_a": str(design_a), "design_b": str(design_b),
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
        f"  1. {design_a}\n"
        f"  2. {design_b}\n\n"
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

    # Exclude synthesized events (from activity_replay) so hook-gap windows
    # don't inflate the cumulative LOC count and false-block future edits.
    for e in event_log.iter_all_events(repo_root=repo_root,
                                         include_synthesized=False):
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
    gate4_outcome = latest_for_target[1]
    gate4_blocked = gate4_outcome == "block"
    # P2-b race fix: "info" means runner was spawned but not yet reported
    # pass/block. In enforced mode this is a race risk — treat as pending
    # and block the next edit. In advisory/bootstrap it's tracked but allowed.
    gate4_pending = gate4_outcome == "info"

    runtime_mode = "bootstrap"
    try:
        rt = (repo_root / ".claude" / "runtime.json")
        if rt.exists():
            import json as _json
            runtime_mode = _json.loads(rt.read_text(encoding="utf-8")).get("mode", "bootstrap")
    except Exception:
        pass

    if unresolved == 0 and not gate4_blocked and not (gate4_pending and runtime_mode == "enforced"):
        return

    if gate4_pending and runtime_mode == "enforced" and not gate4_blocked and unresolved == 0:
        event_log.append_event(
            gate="02", outcome="block", actor="claude", file_path=target_file,
            detail={"tier": size["tier"],
                    "reason": "gate-04 runner still pending (race guard)",
                    "gate4_file": target_file, "gate4_ts": latest_for_target[0]},
            repo_root=repo_root,
        )
        emit_block(
            f"BLOCKED by Gate ② (P2-b: Gate ④ pending).\n\n"
            f"Attempted: {target_file} ({size['tier']}, {size['total']} LOC)\n"
            f"The async test runner for this file has not reported pass/block yet.\n"
            f"Last outcome: info (spawned at {latest_for_target[0]}).\n\n"
            f"How to unblock:\n"
            f"  - Wait a few seconds and retry (runner typically completes <10s).\n"
            f"  - Or check .claude/test-runs/ for the latest log.\n"
            f"  - Advisory/bootstrap mode skips this guard; only enforced mode blocks."
        )

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
        # Accept new key (direction_check_file) + legacy (codex_response_file)
        ref_file = (detail.get("direction_check_file")
                    or detail.get("codex_response_file", ""))
        if not ref_file:
            continue
        ref_abs = repo_root / ref_file
        if not ref_abs.exists() or ref_abs.stat().st_size < 50:
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
        f"   {{\"direction_check_file\":\"...\", \"summary\":\"...\", \"tier\":\"{size['tier']}\"}}"
    )


_EDIT_VERBS = (
    r"edit|modif(?:y|ies|ied)|writ(?:e|es|ing)|chang(?:e|es|ing)|"
    r"updat(?:e|es|ing)|patch(?:es|ed|ing)?|rewrit(?:e|es|ing)|"
    r"append(?:s|ed|ing)?|replac(?:e|es|ing)|delet(?:e|es|ing)|"
    r"remov(?:e|es|ing)|touch(?:es|ed|ing)?|creat(?:e|es|ing)|"
    r"add(?:s|ed|ing)?\s+(?:to|code|lines?)|"
    r"수정|편집|변경|추가|작성|덮어쓰|고쳐|고침"
)
_EDIT_VERB_RE = re.compile(_EDIT_VERBS, re.IGNORECASE)

# Negation markers — edit verb preceded by these does NOT count as intent.
_NEGATION_RE = re.compile(
    r"(?:do\s+not|don['’]t|never|without|never?\s+touch|"
    r"must\s+not|avoid|forbidden|no\s+edits?\s+to|"
    r"하지\s*말|않\s*고|금지)\s*\S{0,40}$",
    re.IGNORECASE,
)


def gate_11_subagent_preflight(repo_root: Path, tool_input: dict) -> None:
    """Gate ⑪ — Task/Agent tool preflight.

    Claude's Agent (a.k.a. Task) tool spawns a subagent. Before dispatch,
    verify that the prompt does not claim write access to any protected
    path. Advisory in bootstrap/advisory mode, blocking in enforced mode.

    Heuristic:
      1. For each protected base path, locate every mention (strips
         backticks/quotes/trailing punctuation around paths).
      2. Within ±120 chars of the mention, look for an edit-verb regex.
      3. If the edit-verb is immediately preceded by a negation phrase
         ("do not", "never", "하지 말"), treat as a prohibition, not intent.
      4. Skip paths that appear only inside a "forbidden" / "protected"
         directive (heuristically detected by header line).
    """
    prompt_text = tool_input.get("prompt", "") or ""
    if not isinstance(prompt_text, str) or not prompt_text:
        return

    ensure_harness_importable(repo_root)
    try:
        from protected_paths import PROTECTED_GLOBS  # type: ignore
    except Exception:
        return

    hits: list[str] = []
    normalized = prompt_text
    # Strip backticks around paths so `.claude/hooks/foo.py` matches base ".claude/hooks"
    normalized_for_scan = re.sub(r"[`\"']", " ", normalized)

    for glob in PROTECTED_GLOBS:
        base = glob.rstrip("/*").rstrip("/")
        if not base or base in (".", ""):
            continue
        # Word-boundary search — avoid matching "CLAUDE.md" inside "CLAUDE.md-like"
        pat = re.compile(r"(?<![\w/.])" + re.escape(base) + r"(?![\w])",
                          re.IGNORECASE)
        for m in pat.finditer(normalized_for_scan):
            start, end = m.start(), m.end()
            win_start = max(0, start - 120)
            win_end = min(len(normalized_for_scan), end + 120)
            window = normalized_for_scan[win_start:win_end]

            verb_m = _EDIT_VERB_RE.search(window)
            if not verb_m:
                continue

            # Check negation: text before the verb in the window
            before_verb = window[:verb_m.start()]
            if _NEGATION_RE.search(before_verb):
                continue

            # Skip if the mention is inside a "forbidden:" / "Do NOT touch" header block
            line_start = normalized_for_scan.rfind("\n", 0, start) + 1
            line = normalized_for_scan[line_start:normalized_for_scan.find("\n", start) if normalized_for_scan.find("\n", start) != -1 else len(normalized_for_scan)]
            if re.match(r"\s*(?:forbidden|protected|do\s*not\s*touch|do\s*not\s*edit|금지)",
                         line, re.IGNORECASE):
                continue

            hits.append(base)
            break  # one hit per protected base is enough

    if not hits:
        return

    import event_log  # type: ignore
    detail = {"protected_mentions": hits[:5],
              "subagent_type": tool_input.get("subagent_type", ""),
              "description": tool_input.get("description", "")}

    # Check runtime mode
    mode = "bootstrap"
    try:
        import json as _json
        rt = repo_root / ".claude" / "runtime.json"
        if rt.exists():
            mode = _json.loads(rt.read_text(encoding="utf-8")).get("mode", "bootstrap")
    except Exception:
        pass

    if mode == "enforced":
        event_log.append_event(
            gate="11", outcome="block", actor="claude",
            file_path="(Agent tool)", detail=detail, repo_root=repo_root,
        )
        emit_block(
            "BLOCKED by Gate ⑪ (subagent preflight).\n\n"
            f"Agent prompt mentions protected paths alongside edit verbs:\n"
            + "\n".join(f"  - {h}" for h in hits[:5]) +
            "\n\nIn enforced mode, dispatching a subagent that may write "
            "to protected paths is rejected. Options:\n"
            "  1. Remove the protected-path mentions from the prompt\n"
            "  2. Handle the change in the main session (Gate ⑦ applies)\n"
            "  3. Drop to advisory mode if this is intentional"
        )

    # Advisory in non-enforced modes
    event_log.append_event(
        gate="11", outcome="advisory", actor="claude",
        file_path="(Agent tool)", detail={**detail, "mode": mode},
        repo_root=repo_root,
    )


def _main_impl() -> None:
    raw = sys.stdin.read()
    try:
        event = json.loads(raw) if raw else {}
    except json.JSONDecodeError:
        event = {}

    repo_root = resolve_repo_root(event.get("cwd") if event else None)
    tool_name = extract_tool_name(event)

    # Gate ⑪ fires on Task (Agent) tool calls — before gate_7 / gate_6 etc.
    if tool_name in ("Task", "Agent"):
        tool_input = extract_tool_input(event)
        gate_11_subagent_preflight(repo_root, tool_input)
        emit_continue(event_name="PreToolUse")

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
    # Test-only bypass: unit tests set this env var to exercise gate logic
    # regardless of circuit breaker state. NEVER set this in regular runs —
    # the variable is explicitly checked against the literal sentinel below.
    _test_bypass = os.environ.get("CLAUDE_HARNESS_TEST_BYPASS_CIRCUIT", "") == "1"
    if _circuit_check is not None and not _test_bypass:
        _disabled, _reason = _circuit_check(_HOOK)
        if _disabled:
            # Fail-closed on tripped (auto-disabled by repeated failures):
            # a broken gate hook must not silently drop enforcement.
            _severity = _circuit_severity(_HOOK) if _circuit_severity else "tripped"
            if _severity == "tripped":
                from common import emit_block
                emit_block(
                    "BLOCKED: pre_tool_use hook auto-disabled by circuit breaker "
                    "(consecutive failures). Refusing to proceed without Layer 3 "
                    "enforcement.\n\n"
                    f"{_reason}\n\n"
                    "Investigate the failure reason, fix the root cause, then reset."
                )
            # Manual disable (maintenance) → pass-through, user-authorized.
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
