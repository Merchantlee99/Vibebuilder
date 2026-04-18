#!/usr/bin/env python3
"""
protected_paths.py — Single source of truth for harness control-plane paths.

Gate ⑦ (`.claude/hooks/common.py:is_protected_path`) and the subagent
planner (`subagent_planner.py`) both need to know which paths are
protected. This module exposes them in two canonical forms:

  - PROTECTED_REGEX: list[re.Pattern]  — used by hooks for `search()`
  - PROTECTED_GLOBS: list[str]         — used by subagent_planner for
                                         glob-style conflict detection

Both are derived from the same PROTECTED_DECLS list. Do NOT redefine
the list elsewhere — import from here.
"""

from __future__ import annotations

import re


# Canonical declarations. Each entry is a regex pattern string anchored at
# the repo root (no leading slash). Globs are derived by stripping the `^`,
# escaping, and appending `**` for directory-style patterns.
PROTECTED_DECLS = [
    (r"^\.claude/hooks/",             "dir"),
    (r"^\.claude/sealed-prompts/",    "dir"),
    (r"^\.claude/settings\.local\.json$", "file"),
    (r"^\.claude/events\.jsonl$",     "file"),
    (r"^\.claude/learnings\.jsonl$",  "file"),
    (r"^\.claude/audits/",            "dir"),
    (r"^\.claude/runtime\.json$",     "file"),
    (r"^\.claude/manifests/",         "dir"),
    (r"^\.claude/playbooks/",         "dir"),
    (r"^\.claude/plugins\.lock$",     "file"),
    (r"^scripts/harness/",            "dir"),
    (r"^CLAUDE\.md$",                 "file"),
    (r"^AGENTS\.md$",                 "file"),
    (r"^ETHOS\.md$",                  "file"),
    (r"^\.gitignore$",                "file"),
]

PROTECTED_REGEX = [re.compile(p) for p, _ in PROTECTED_DECLS]


def _regex_to_glob(pattern: str, kind: str) -> str:
    """Convert an anchored regex pattern to a simple glob.

    Handles the subset of regex syntax actually used in PROTECTED_DECLS:
      - leading `^`, trailing `$`
      - `\\.` escaping (becomes `.`)

    Raises ValueError if the regex contains unsupported metacharacters
    (|, +, *, ?, [], (), {}) so future drift is caught loudly.
    """
    s = pattern
    if s.startswith("^"):
        s = s[1:]
    if s.endswith("$"):
        s = s[:-1]
    # Replace escaped dots first
    s = s.replace(r"\.", ".")
    # Detect unescaped regex metacharacters — we only allow path chars + `.`
    forbidden = re.compile(r"[|+*?\[\](){}\\]")
    if forbidden.search(s):
        raise ValueError(
            f"_regex_to_glob: pattern {pattern!r} contains unsupported "
            f"regex metachars (only `^`, `$`, `\\.` are supported). "
            f"Update _regex_to_glob or simplify the pattern.")
    if kind == "dir":
        return s + "**" if s.endswith("/") else s + "/**"
    return s


PROTECTED_GLOBS = [_regex_to_glob(p, k) for p, k in PROTECTED_DECLS]


def is_protected(rel_path: str):
    """Return the matched pattern (re.Pattern) or None."""
    for pat in PROTECTED_REGEX:
        if pat.search(rel_path):
            return pat
    return None
