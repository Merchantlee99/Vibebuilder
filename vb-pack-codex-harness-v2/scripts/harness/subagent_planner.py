#!/usr/bin/env python3
"""Plan subagent dispatches and claim write ownership."""

from __future__ import annotations

import argparse
import sys

from common import ROOT, append_jsonl, load_json, path_list_overlap, utc_slug, write_json


CLAIMS_PATH = ROOT / "harness" / "context" / "ownership-claims.json"
LOG_PATH = ROOT / "harness" / "telemetry" / "subagent-events.jsonl"

READ_ONLY_ROLES = {
    "pm_strategist",
    "pm_redteam",
    "docs_researcher",
    "code_mapper",
    "task_distributor",
    "reviewer",
    "security_auditor",
    "browser_debugger",
    "explorer",
}


def load_claims() -> list[dict]:
    claims = load_json(CLAIMS_PATH, [])
    return claims if isinstance(claims, list) else []


def active_claims() -> list[dict]:
    return [claim for claim in load_claims() if claim.get("status") == "active"]


def save_claims(claims: list[dict]) -> None:
    write_json(CLAIMS_PATH, claims)


def default_mode(role: str, write_scope: list[str]) -> str:
    if role in READ_ONLY_ROLES or not write_scope:
        return "read-only"
    return "worktree"


def plan(args: argparse.Namespace) -> int:
    mode = args.mode or default_mode(args.role, args.write_scope)
    if mode == "read-only" and args.write_scope:
        print("ERROR: read-only subagents cannot claim write_scope", file=sys.stderr)
        return 1
    if args.tier == "high-risk" and args.write_scope and mode == "local":
        print("ERROR: high-risk write-scoped subagents must use worktree or cloud mode", file=sys.stderr)
        return 1
    if args.tier == "high-risk" and args.write_scope and not args.claim:
        print("ERROR: high-risk write-scoped subagents must use --claim", file=sys.stderr)
        return 1

    conflicts = []
    for claim in active_claims():
        if claim.get("owner") == args.owner:
            continue
        if path_list_overlap(args.write_scope, claim.get("write_scope", [])):
            conflicts.append(claim)

    if conflicts:
        for conflict in conflicts:
            print(
                f"ERROR: write scope conflicts with active owner {conflict.get('owner')}: {conflict.get('write_scope')}",
                file=sys.stderr,
            )
        return 1

    dispatch = {
        "id": f"dispatch-{utc_slug()}",
        "role": args.role,
        "owner": args.owner,
        "goal": args.goal,
        "tier": args.tier,
        "mode": mode,
        "read_scope": args.read_scope,
        "write_scope": args.write_scope,
        "forbidden_paths": args.forbidden_path,
        "stop_condition": args.stop_condition,
        "expected_artifact": args.expected_artifact,
        "validation": args.validation,
    }

    if args.claim and args.write_scope:
        claims = load_claims()
        claim = {
            "id": dispatch["id"],
            "owner": args.owner,
            "role": args.role,
            "goal": args.goal,
            "tier": args.tier,
            "write_scope": args.write_scope,
            "status": "active",
            "created_at": utc_slug(),
        }
        claims.append(claim)
        save_claims(claims)
        append_jsonl(LOG_PATH, {"event": "claim", **claim})

    print(render_dispatch(dispatch))
    return 0


def render_dispatch(dispatch: dict) -> str:
    lines = [
        f"role: {dispatch['role']}",
        f"owner: {dispatch['owner']}",
        f"goal: {dispatch['goal']}",
        f"mode: {dispatch['mode']}",
        f"read_scope: {dispatch['read_scope']}",
        f"write_scope: {dispatch['write_scope']}",
        f"forbidden_paths: {dispatch['forbidden_paths']}",
        f"stop_condition: {dispatch['stop_condition']}",
        f"expected_artifact: {dispatch['expected_artifact']}",
        f"validation: {dispatch['validation']}",
    ]
    return "\n".join(lines)


def release(args: argparse.Namespace) -> int:
    claims = load_claims()
    changed = False
    for claim in claims:
        if claim.get("owner") == args.owner and claim.get("status") == "active":
            claim["status"] = "released"
            claim["released_at"] = utc_slug()
            changed = True
            append_jsonl(LOG_PATH, {"event": "release", **claim})
    if not changed:
        print(f"WARN: no active claims for owner {args.owner}")
    save_claims(claims)
    return 0


def list_claims(_: argparse.Namespace) -> int:
    claims = active_claims()
    if not claims:
        print("no active claims")
        return 0
    for claim in claims:
        print(f"{claim.get('owner')}: {claim.get('write_scope')} ({claim.get('goal')})")
    return 0


def check(args: argparse.Namespace) -> int:
    claims = active_claims()
    errors = []
    for idx, left in enumerate(claims):
        for right in claims[idx + 1:]:
            if path_list_overlap(left.get("write_scope", []), right.get("write_scope", [])):
                errors.append(f"{left.get('owner')} conflicts with {right.get('owner')}")
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    if args.quiet:
        return 0
    print("ownership ok")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("plan")
    p.add_argument("--role", required=True)
    p.add_argument("--owner", required=True)
    p.add_argument("--goal", required=True)
    p.add_argument("--tier", choices=["trivial", "normal", "high-risk"], default="normal")
    p.add_argument("--mode", choices=["read-only", "workspace-write", "worktree", "cloud"])
    p.add_argument("--read-scope", action="append", default=[])
    p.add_argument("--write-scope", action="append", default=[])
    p.add_argument("--forbidden-path", action="append", default=[])
    p.add_argument("--stop-condition", default="Return the requested artifact and stop.")
    p.add_argument("--expected-artifact", default="Concise handoff report.")
    p.add_argument("--validation", default="State what was checked and what remains unverified.")
    p.add_argument("--claim", action="store_true")

    r = sub.add_parser("release")
    r.add_argument("--owner", required=True)

    sub.add_parser("list")

    c = sub.add_parser("check")
    c.add_argument("--quiet", action="store_true")

    args = parser.parse_args()
    if args.command == "plan":
        return plan(args)
    if args.command == "release":
        return release(args)
    if args.command == "list":
        return list_claims(args)
    if args.command == "check":
        return check(args)
    raise AssertionError(args.command)


if __name__ == "__main__":
    raise SystemExit(main())
