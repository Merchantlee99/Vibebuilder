#!/usr/bin/env python3
"""
post_tool_use.py — Unified Post-Edit hook. Runs Gate ②/③/④/⑥/⑧/⑨ + Layer 4
memory sync.

Gate ⑥ (scope tracking)     — record edit-tracked event
Gate ② (review-needed)      — for non-trivial edits
Gate ④ (test execution)     — background deterministic toolchain
Gate ③ (learning record)    — auto-generate from recent blocks
Gate ⑧ (claim verification) — markdown/code/Bash content scan
Gate ⑨ (trust boundary)     — external tool response scan
Layer 4 memory_manager.sync_turn() — post-turn learning commit
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import (
    ensure_harness_importable, emit_continue, extract_tool_input,
    extract_tool_name, load_event, resolve_repo_root, run_size_check,
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



# ── Gate ⑥ record (non-blocking) ───────────────────────────────────


def gate_6_track(repo_root: Path, size: dict) -> None:
    ensure_harness_importable(repo_root)
    import event_log  # type: ignore
    event_log.append_event(
        gate="06", outcome="edit-tracked", actor="claude",
        file_path=size["file_path"],
        detail={"added": size["added"], "removed": size["removed"],
                "total_loc": size["total"], "edit_tier": size["tier"],
                "complexity": size["complexity"], "reason": "edit-tracked"},
        repo_root=repo_root,
    )


# ── Gate ② (review-needed marker) ──────────────────────────────────


def gate_2_review_needed(repo_root: Path, size: dict) -> None:
    if size["tier"] == "trivial":
        return
    ensure_harness_importable(repo_root)
    import event_log  # type: ignore

    # author_actor is hardcoded: this session is always Claude. Do NOT read from
    # env/config — that would let the author forge `user` and bypass Gate ② P2-F.
    author_actor = "claude"

    # Pick sealed prompt by file type and path. In solo mode, the expected
    # reviewer actor is `user` (human) or `claude-reviewer` (isolated session).
    fp = (size["file_path"] or "").lower()
    if any(fp.startswith(p) for p in (".claude/hooks/", ".claude/sealed-prompts/",
                                       "scripts/harness/", ".claude/settings.local.json")):
        sealed = "review-code.md"
        reviewer = "user"
        author_aware = "harness-path"
    elif fp.endswith((".md", ".mdx", ".txt", ".rst")) or any(
            fp.startswith(p) for p in ("plans/", "docs/", "specs/", "notes/")):
        sealed = "review-plan.md"
        reviewer = "user"
        author_aware = "standard"
    else:
        sealed = "review-code.md"
        reviewer = "user"
        author_aware = "standard"

    event_log.append_event(
        gate="02", outcome="review-needed", actor=author_actor,
        file_path=size["file_path"],
        detail={"tier": size["tier"], "complexity": size["complexity"],
                "added": size["added"], "removed": size["removed"],
                "total_loc": size["total"],
                "reviewer_expected": reviewer,
                "suggested_sealed_prompt": f".claude/sealed-prompts/{sealed}",
                "author_aware": author_aware,
                "instruction": "opposite actor must red-team this change"},
        repo_root=repo_root,
    )


# ── Gate ④ (test execution) — background ───────────────────────────


def gate_4_test(repo_root: Path, size: dict) -> None:
    """Detect project toolchain + spawn background test runner.

    Docs-only files → skip event only.
    Code files → fork a detached subprocess that runs available tools
    (ruff / mypy / pytest / npm lint+test) and records outcome
    (pass|block) to events.jsonl when done. Hook returns immediately
    so editor UX stays snappy.

    Layer 2 Gate ② Pre reads the latest per-file Gate ④ outcome for
    enforcement.
    """
    fp = size["file_path"]
    if not fp:
        return

    ensure_harness_importable(repo_root)
    import event_log  # type: ignore

    # Docs-only short-circuit
    if fp.endswith((".md", ".mdx", ".txt", ".rst")) or any(
            fp.startswith(p) for p in ("plans/", "docs/", "specs/", "notes/")):
        event_log.append_event(
            gate="04", outcome="skip", actor="system", file_path=fp,
            detail={"reason": "docs-only"}, repo_root=repo_root,
        )
        return

    # Spawn detached runner. Runner script is a sibling to this hook.
    runner = Path(__file__).parent / "gate_4_runner.py"
    if not runner.exists():
        event_log.append_event(
            gate="04", outcome="skip", actor="system", file_path=fp,
            detail={"reason": "runner script missing"}, repo_root=repo_root,
        )
        return

    import subprocess as _sp
    try:
        # Detach via start_new_session so it survives the parent hook exit.
        _sp.Popen(
            ["python3", str(runner), str(repo_root), fp],
            stdout=_sp.DEVNULL, stderr=_sp.DEVNULL,
            start_new_session=True, cwd=str(repo_root),
        )
    except Exception as exc:
        event_log.append_event(
            gate="04", outcome="skip", actor="system", file_path=fp,
            detail={"reason": f"runner spawn failed: {exc}"},
            repo_root=repo_root,
        )
        return

    # Record an intent event so the caller can tell the runner was launched.
    event_log.append_event(
        gate="04", outcome="info", actor="system", file_path=fp,
        detail={"reason": "runner spawned (async)", "runner": str(runner)},
        repo_root=repo_root,
    )


# ── Gate ⑧ (claim verification) ─────────────────────────────────────


def gate_8_claim_verify(repo_root: Path, tool_name: str, tool_input: dict) -> None:
    """Scan markdown/code/Bash content for false protected-path claims."""
    content = ""
    file_path = ""

    if tool_name in ("Edit", "Write", "NotebookEdit"):
        file_path = tool_input.get("file_path") or tool_input.get("notebook_path") or ""
        if not file_path:
            return
        ext = Path(file_path).suffix.lower()
        if ext not in (".md", ".mdx", ".txt", ".rst",
                       ".py", ".sh", ".bash", ".yml", ".yaml",
                       ".toml", ".json", ".jsonl"):
            return
        if tool_name == "Write":
            content = tool_input.get("content", "") or ""
        elif tool_name == "Edit":
            content = tool_input.get("new_string", "") or ""
        elif tool_name == "NotebookEdit":
            content = tool_input.get("new_source", "") or ""
    elif tool_name == "Bash":
        cmd = tool_input.get("command", "") or ""
        if not isinstance(cmd, str):
            return
        content = cmd
        file_path = "(bash-command)"
    else:
        return

    if not content:
        return

    # Load Gate ⑦ protected regex from common.py
    from common import PROTECTED_REGEX  # type: ignore

    claim_re = re.compile(
        r"(?:`)?([\.\w/\-]+\.(?:json|jsonl|sh|py|md|txt))(?:`)?\s+(?:is|was|are)\s+"
        r"(?:not\s+protected|unprotected|safe\s+to\s+edit|free\s+to\s+edit)",
        re.IGNORECASE,
    )

    hits: list[dict] = []
    for m in claim_re.finditer(content):
        path_claim = m.group(1)
        matched = None
        for rx in PROTECTED_REGEX:
            if rx.search(path_claim):
                matched = rx.pattern
                break
        if matched is not None:
            hits.append({"claim": path_claim, "claimed": "not protected",
                         "actual": "protected by Gate ⑦", "matched_pattern": matched})

    if not hits:
        return

    ensure_harness_importable(repo_root)
    try:
        import event_log  # type: ignore
        event_log.append_event(
            gate="08", outcome="claim-failed", actor="claude",
            file_path=file_path,
            detail={"hit_count": len(hits), "hits": hits[:5],
                    "advisory": "false protected-path claim detected"},
            repo_root=repo_root,
        )
    except Exception:
        pass

    sys.stderr.write(
        f"Gate ⑧ — claim verification: {len(hits)} false claim(s) in {file_path}.\n"
    )
    for h in hits[:3]:
        sys.stderr.write(f"  '{h['claim']}' claimed {h['claimed']} but is {h['actual']}\n")


# ── Gate ⑨ (trust boundary) ─────────────────────────────────────────


def gate_9_trust(repo_root: Path, tool_name: str, tool_response: dict) -> None:
    # MCP tool names start with "mcp__<server>__<tool>". Treat ALL MCP
    # responses as external untrusted data (same class as WebFetch).
    is_mcp = isinstance(tool_name, str) and tool_name.startswith("mcp__")
    if tool_name not in ("WebFetch", "WebSearch", "Bash") and not is_mcp:
        return
    text = ""
    if isinstance(tool_response, dict):
        for k in ("text", "output", "stdout", "content", "results", "body"):
            v = tool_response.get(k)
            if isinstance(v, str) and v:
                text = v
                break
    if not text or len(text) < 50:
        return

    scan = text[:20000]
    patterns = [
        (r"ignore\s+(?:all\s+)?(?:previous|prior|the\s+above)\s+instructions", "ignore-previous"),
        (r"forget\s+(?:your|all|everything|the\s+above)", "forget-training"),
        (r"(?:disable|turn\s+off|skip|bypass)\s+(?:auth|authentication|verification|safety)", "disable-safety"),
        (r"new\s+instructions?\s*:", "new-instructions-marker"),
        (r"INSTRUCTIONS?\s+OVERRIDE", "instructions-override"),
        (r"you\s+are\s+now\s+(?:a|an|the)\s+\w+", "persona-hijack"),
        (r"(?:^|\n)\s*system\s*:\s*", "fake-system-message"),
        (r"</?(?:system|trusted|admin|root)>", "fake-trust-tag"),
    ]

    hits: list[dict] = []
    for pat, label in patterns:
        m = re.search(pat, scan, re.IGNORECASE | re.MULTILINE)
        if m:
            snippet = scan[max(0, m.start()-40):m.end()+40].replace("\n", " ")
            hits.append({"label": label, "snippet": snippet[:200]})

    if not hits:
        return

    ensure_harness_importable(repo_root)
    try:
        import event_log  # type: ignore
        event_log.append_event(
            gate="09", outcome="injection-candidate", actor="external",
            file_path=tool_name,
            detail={"tool": tool_name, "hit_count": len(hits),
                    "hits": hits[:5], "advisory": "untrusted data contains injection patterns"},
            repo_root=repo_root,
        )
    except Exception:
        pass

    sys.stderr.write(f"Gate ⑨ — {len(hits)} prompt-injection pattern(s) in {tool_name}.\n")
    for h in hits[:3]:
        sys.stderr.write(f"  [{h['label']}] ...{h['snippet'][:100]}...\n")


# ── Layer 4: memory_manager sync ───────────────────────────────────


def layer_4_sync(repo_root: Path, event: dict) -> None:
    ensure_harness_importable(repo_root)
    try:
        import memory_manager  # type: ignore
        memory_manager.sync_turn(event=event, repo_root=repo_root)
    except Exception:
        pass


# ── main ────────────────────────────────────────────────────────────


def _main_impl() -> None:
    raw = sys.stdin.read()
    try:
        event = json.loads(raw) if raw else {}
    except json.JSONDecodeError:
        event = {}

    repo_root = resolve_repo_root(event.get("cwd") if event else None)
    tool_name = extract_tool_name(event)
    tool_input = extract_tool_input(event)
    tool_response = event.get("tool_response") or {}
    if not isinstance(tool_response, dict):
        tool_response = {}

    # Gate ⑨ runs on external-data tools regardless of mutation
    gate_9_trust(repo_root, tool_name, tool_response)

    # Gate ⑧ runs on content-writing tools + Bash
    gate_8_claim_verify(repo_root, tool_name, tool_input)

    # For file-mutating tools, run size-based gates
    if tool_mutates_repo(tool_name):
        size = run_size_check(repo_root, raw)
        if size["file_path"]:
            gate_6_track(repo_root, size)
            gate_2_review_needed(repo_root, size)
            gate_4_test(repo_root, size)

    # For Bash, run bash_write_probe to detect tee/sed/printf/install writes
    if tool_name == "Bash":
        cmd = tool_input.get("command", "") or ""
        if isinstance(cmd, str) and cmd:
            ensure_harness_importable(repo_root)
            try:
                import bash_write_probe  # type: ignore
                writes = bash_write_probe._extract_writes(cmd)
                if writes:
                    import event_log  # type: ignore
                    for target, loc in writes:
                        tgt = bash_write_probe._normalize_target(target, repo_root)
                        if not tgt or tgt.startswith("/dev/"):
                            continue
                        event_log.append_event(
                            gate="06", outcome="edit-tracked", actor="bash",
                            file_path=tgt,
                            detail={"added": loc, "removed": 0, "total_loc": loc,
                                    "edit_tier": "bash-synth",
                                    "reason": "bash-write bypass synthesized"},
                            repo_root=repo_root,
                        )
            except Exception:
                pass

    # Layer 4: sync turn outcome
    layer_4_sync(repo_root, event)

    emit_continue(event_name="PostToolUse")



def main() -> None:
    _HOOK = "post_tool_use"
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
