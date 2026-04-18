#!/usr/bin/env python3
"""
bash_write_probe.py — Detect file-write patterns in Bash tool_input.command.

Closes the Bash-bypass loophole where AI uses heredoc / tee / sed -i / printf
> file / install to write files without triggering Edit|Write hooks.

Exported:
  _extract_writes(cmd)       → list[(target, loc_estimate)]
  _normalize_target(target, root) → repo-relative or absolute outside-repo path

Called from hooks/post_tool_use.py when tool_name == "Bash".
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path


_HEREDOC_RE = re.compile(
    r""">+\s*([^\s<>|&;]+)\s*<<-?\s*(?:(['"])(\w+)\2|(\w+))"""
)

_PLAIN_REDIRECT_RE = re.compile(
    r""">>?\s*([^\s<>|&;]+)\s*(?:$|[;&|])"""
)

_TEE_RE = re.compile(
    r"""\btee\s+(?:-a\s+|--append\s+)?([^\s<>|&;-][^\s<>|&;]*)"""
)

_SED_INPLACE_RE = re.compile(
    r"""\bsed\s+-i(?:\.\w+)?(?:\s+(?:-[a-zA-Z]\s+)?['"][^'"]*['"])*\s+([^\s;|&]+)"""
)

_PRINTF_REDIRECT_RE = re.compile(
    r"""\bprintf\s+(['"])(.+?)\1\s+(?:[^\s<>|&;]*\s+)*>>?\s*([^\s<>|&;]+)"""
)

_INSTALL_RE = re.compile(
    r"""\binstall\s+(?:-[a-zA-Z]+\s+\S+\s+)*(\S+)\s+(\S+)\s*(?:$|[;&|])"""
)


def _extract_writes(cmd):
    writes = []
    for m in _HEREDOC_RE.finditer(cmd):
        target = m.group(1)
        delim = m.group(3) or m.group(4)
        if not delim:
            continue
        body_pat = re.compile(
            r"<<-?\s*['\"]?" + re.escape(delim) + r"['\"]?\s*\n(.*?)(?:^|\n)" + re.escape(delim) + r"\b",
            re.DOTALL | re.MULTILINE,
        )
        bm = body_pat.search(cmd)
        loc = len(bm.group(1).splitlines()) if bm else 0
        writes.append((target, loc))

    for m in _PRINTF_REDIRECT_RE.finditer(cmd):
        fmt = m.group(2)
        target = m.group(3)
        loc = max(1, fmt.count("\\n"))
        writes.append((target, loc))

    for m in _TEE_RE.finditer(cmd):
        writes.append((m.group(1), 1))

    for m in _SED_INPLACE_RE.finditer(cmd):
        writes.append((m.group(1), 1))

    for m in _INSTALL_RE.finditer(cmd):
        writes.append((m.group(2), 1))

    if not writes:
        for m in _PLAIN_REDIRECT_RE.finditer(cmd):
            writes.append((m.group(1), 1))

    seen = set()
    deduped = []
    for t, loc in writes:
        key = (t, loc)
        if key not in seen:
            seen.add(key)
            deduped.append((t, loc))
    return deduped


def _normalize_target(target, root):
    tgt = str(target).replace("\\", "/")
    while tgt.startswith("./"):
        tgt = tgt[2:]
    root_str = str(root)
    if tgt.startswith("/"):
        try:
            rel = os.path.relpath(tgt, root_str)
        except ValueError:
            return tgt
        if rel.startswith("../"):
            return tgt
        return rel.replace("\\", "/")
    return tgt


def main():
    if len(sys.argv) < 2:
        return 0
    root = Path(sys.argv[1])
    try:
        raw = sys.stdin.read()
        payload = json.loads(raw)
    except Exception:
        return 0
    if payload.get("hook_event_name") != "PostToolUse":
        return 0
    if payload.get("tool_name") != "Bash":
        return 0
    cmd = (payload.get("tool_input") or {}).get("command") or ""
    if not isinstance(cmd, str) or not cmd:
        return 0
    writes = _extract_writes(cmd)
    if not writes:
        return 0
    sys.path.insert(0, str(root / "scripts" / "harness"))
    try:
        import event_log
    except Exception:
        return 0
    for target, loc in writes:
        tgt = _normalize_target(target, root)
        if not tgt:
            continue
        if tgt.startswith("/dev/") or tgt == "/dev/null":
            continue
        try:
            event_log.append_event(
                gate="06", outcome="edit-tracked", actor="bash",
                file_path=tgt,
                detail={"added": loc, "removed": 0, "total_loc": loc,
                        "edit_tier": "bash-synth",
                        "reason": "bash-write bypass synthesized"},
            )
        except Exception:
            continue
    return 0


if __name__ == "__main__":
    sys.exit(main())
