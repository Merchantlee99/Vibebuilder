#!/usr/bin/env python3
"""
subagent_planner.py — Preflight + ownership claim for Claude Agent dispatch.

Before calling the Claude `Agent` tool for a worker-kind task, run:

    python3 scripts/harness/subagent_planner.py plan \
        --role worker --owner worker-auth \
        --goal "implement auth slice" \
        --write-scope src/auth --write-scope tests/auth \
        --claim

This:
  1. Validates role exists in .claude/manifests/subagents.yaml
  2. Checks write_scope against protected_paths (blocks if any match)
  3. Checks ownership.json for conflicts (another owner holds same path)
  4. If --claim, records ownership in .claude/context/ownership.json
  5. Prints a dispatch_prompt ready to paste into Agent(prompt=...)
  6. Appends event (gate="11" subagent-preflight) to events.jsonl

Subcommands:
  plan      — preflight + optional claim (above)
  release   — release ownership after subagent returns
  list      — show active claims
  validate  — check all claims for stale / orphaned entries
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "harness"))

OWNERSHIP_PATH = REPO_ROOT / ".claude" / "context" / "ownership.json"
MANIFEST_PATH = REPO_ROOT / ".claude" / "manifests" / "subagents.json"


def _load_manifest_yaml() -> dict:
    """Load JSON manifest (avoids pyyaml dep)."""
    if not MANIFEST_PATH.exists():
        return {}
    try:
        data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    # Override protected_paths from canonical source to avoid drift.
    try:
        from protected_paths import PROTECTED_GLOBS  # type: ignore
        data.setdefault("defaults", {})["protected_paths"] = list(PROTECTED_GLOBS)
    except Exception:
        pass
    return data


def _load_ownership() -> dict:
    if not OWNERSHIP_PATH.exists():
        return {"claims": []}
    try:
        return json.loads(OWNERSHIP_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"claims": []}


def _save_ownership(data: dict) -> None:
    OWNERSHIP_PATH.parent.mkdir(parents=True, exist_ok=True)
    OWNERSHIP_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n",
                              encoding="utf-8")


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _glob_conflict(a: str, b: str) -> bool:
    """Overlap check with path-boundary awareness.

    Returns True iff one path is equal to or a descendant of the other.
    `src/auth` vs `src/authentication` → False (different dirs).
    `src/auth` vs `src/auth/api.py`    → True  (descendant).
    `.claude/hooks/**` vs `.claude/hooks/foo.py` → True.
    """
    def _strip(s: str) -> str:
        while s.endswith(("/**", "/*", "**", "*", "/")):
            if s.endswith("/**"):
                s = s[:-3]
            elif s.endswith("/*"):
                s = s[:-2]
            elif s.endswith("**"):
                s = s[:-2]
            elif s.endswith("*"):
                s = s[:-1]
            elif s.endswith("/"):
                s = s[:-1]
        return s
    a_base = _strip(a)
    b_base = _strip(b)
    if not a_base or not b_base:
        return False
    if a_base == b_base:
        return True
    # Require path boundary: `x` descends from `y` only if x starts with y+"/"
    return (a_base.startswith(b_base + "/")
            or b_base.startswith(a_base + "/"))


def _protected_hit(write_scope: list[str], protected: list[str]) -> str | None:
    for ws in write_scope:
        for p in protected:
            if _glob_conflict(ws, p):
                return f"{ws} overlaps protected {p}"
    return None


def _event_append(gate: str, outcome: str, detail: dict, file_path: str = "") -> None:
    try:
        import event_log  # type: ignore
        event_log.append_event(
            gate=gate, outcome=outcome, actor="claude",
            file_path=file_path, detail=detail, repo_root=REPO_ROOT,
        )
    except Exception:
        pass


def plan(args) -> int:
    manifest = _load_manifest_yaml()
    roles = manifest.get("roles", {})
    role = roles.get(args.role)
    if not role:
        print(f"unknown role: {args.role} (known: {sorted(roles)})", file=sys.stderr)
        return 2

    if role.get("write_scope") == "none" and args.write_scope:
        print(f"role '{args.role}' has write_scope=none but {len(args.write_scope)} "
              "paths given. Remove --write-scope or use a different role.",
              file=sys.stderr)
        return 2

    protected = (manifest.get("defaults") or {}).get("protected_paths", []) or []
    hit = _protected_hit(args.write_scope, protected)
    if hit:
        print(f"BLOCKED: write_scope hits protected path: {hit}", file=sys.stderr)
        _event_append("11", "block",
                      {"reason": "protected_path_overlap", "detail": hit,
                       "role": args.role, "owner": args.owner})
        return 2

    ownership = _load_ownership()
    conflicts = []
    for claim in ownership.get("claims", []):
        if claim.get("owner") == args.owner:
            continue  # same owner re-claiming is fine
        for ws in args.write_scope:
            for existing in claim.get("write_scope", []):
                if _glob_conflict(ws, existing):
                    conflicts.append(
                        f"{ws} conflicts with {claim['owner']}'s {existing}")
    if conflicts:
        print("CONFLICTS:", file=sys.stderr)
        for c in conflicts:
            print(f"  - {c}", file=sys.stderr)
        _event_append("11", "block",
                      {"reason": "ownership_conflict", "conflicts": conflicts,
                       "role": args.role, "owner": args.owner})
        return 2

    dispatch_prompt = _build_dispatch_prompt(role, args)

    spec = {
        "role": args.role,
        "subagent_type": role.get("subagent_type"),
        "owner": args.owner,
        "goal": args.goal,
        "write_scope": args.write_scope,
        "forbidden_paths": protected,
        "default_isolation": role.get("default_isolation"),
        "dispatch_status": "ready",
        "dispatch_prompt": dispatch_prompt,
    }

    if args.claim:
        ownership.setdefault("claims", []).append({
            "owner": args.owner, "role": args.role,
            "write_scope": args.write_scope,
            "claimed_at": _now(), "goal": args.goal,
        })
        _save_ownership(ownership)
        spec["claim_recorded"] = True

    _event_append("11", "pass", {"owner": args.owner, "role": args.role,
                                   "write_scope": args.write_scope,
                                   "claimed": bool(args.claim)})
    print(json.dumps(spec, indent=2, ensure_ascii=False))
    return 0


def _build_dispatch_prompt(role: dict, args) -> str:
    shared = ["Prompt.md", "PRD.md", "Plan.md", "Implement.md"]
    nl = "\n"
    paths = nl.join(f"  - {p}" for p in args.write_scope) or "  - (none)"
    reads = nl.join(f"  - {p}" for p in shared)
    iso = role.get("default_isolation") or "none"
    iso_note = ' — use Agent(isolation="worktree")' if iso == "worktree" else ""
    return (
        f"Goal: {args.goal}\n\n"
        f"Role: {args.role} (subagent_type={role.get('subagent_type')})\n"
        f"Owner: {args.owner}\n"
        f"Default isolation: {iso}{iso_note}\n\n"
        f"Write scope (DO NOT touch anything else):\n{paths}\n\n"
        f"Read these first:\n{reads}\n\n"
        f"Stop condition: {args.stop or 'goal satisfied + tests green in owned scope'}\n"
        f"Validation: {args.validation or 'run the unit tests for the touched modules'}\n\n"
        f"Forbidden: any write outside write_scope, and all protected paths "
        f"(CLAUDE.md, .claude/hooks/, scripts/harness/, etc.)\n"
        f"Report: changed_files, validations_run, remaining_risks."
    )


def release(args) -> int:
    ownership = _load_ownership()
    before = len(ownership.get("claims", []))
    ownership["claims"] = [c for c in ownership.get("claims", [])
                            if c.get("owner") != args.owner]
    _save_ownership(ownership)
    print(f"released: {args.owner} (claims: {before} → {len(ownership['claims'])})")
    _event_append("11", "release", {"owner": args.owner})
    return 0


def list_claims(args) -> int:
    ownership = _load_ownership()
    claims = ownership.get("claims", [])
    if not claims:
        print("  (no active claims)")
        return 0
    for c in claims:
        print(f"  {c.get('owner'):<20} role={c.get('role'):<12} "
              f"scope={','.join(c.get('write_scope', []))}  "
              f"claimed={c.get('claimed_at', '')}")
    return 0


def validate(args) -> int:
    ownership = _load_ownership()
    manifest = _load_manifest_yaml()
    roles = manifest.get("roles", {})
    problems: list[str] = []
    for c in ownership.get("claims", []):
        if c.get("role") not in roles:
            problems.append(f"{c.get('owner')}: unknown role {c.get('role')}")
    if problems:
        for p in problems:
            print(f"  FAIL: {p}")
        return 1
    print(f"  ok: {len(ownership.get('claims', []))} claim(s) valid")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("plan")
    p.add_argument("--role", required=True)
    p.add_argument("--owner", required=True)
    p.add_argument("--goal", required=True)
    p.add_argument("--write-scope", action="append", default=[])
    p.add_argument("--stop", default=None)
    p.add_argument("--validation", default=None)
    p.add_argument("--claim", action="store_true")

    r = sub.add_parser("release")
    r.add_argument("--owner", required=True)

    sub.add_parser("list")
    sub.add_parser("validate")

    args = ap.parse_args()
    if args.cmd == "plan":
        return plan(args)
    if args.cmd == "release":
        return release(args)
    if args.cmd == "list":
        return list_claims(args)
    if args.cmd == "validate":
        return validate(args)
    return 2


if __name__ == "__main__":
    sys.exit(main())
