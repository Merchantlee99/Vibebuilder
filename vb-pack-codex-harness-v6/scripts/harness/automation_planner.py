#!/usr/bin/env python3
"""Create and audit automation intent records."""

from __future__ import annotations

import argparse
import sys

from common import ROOT, append_jsonl, load_json, utc_slug, write_json
from event_log import iter_events, record_event


INTENTS_PATH = ROOT / "harness" / "context" / "automation-intents.json"
LOG_PATH = ROOT / "harness" / "telemetry" / "automation-events.jsonl"
ALLOWED_KINDS = {
    "thread-heartbeat",
    "standalone",
    "weekly-retro",
    "pending-review",
    "stale-task",
    "skill-triage",
}


def load_intents() -> list[dict]:
    intents = load_json(INTENTS_PATH, [])
    return intents if isinstance(intents, list) else []


def save_intents(intents: list[dict]) -> None:
    write_json(INTENTS_PATH, intents)


def add(args: argparse.Namespace) -> int:
    if args.kind not in ALLOWED_KINDS:
        record_event("automation.add", actor="harness", status="blocked", kind=args.kind, reason="unsupported kind")
        print(f"ERROR: unsupported automation kind: {args.kind}", file=sys.stderr)
        return 1
    if args.risk == "high" and not args.requires_approval:
        record_event("automation.add", actor="harness", status="blocked", kind=args.kind, reason="high-risk missing approval")
        print("ERROR: high-risk automations require explicit approval flag", file=sys.stderr)
        return 1

    intent = {
        "id": f"automation-{utc_slug()}",
        "kind": args.kind,
        "title": args.title,
        "prompt": args.prompt,
        "cadence": args.cadence,
        "mode": args.mode,
        "risk": args.risk,
        "requires_approval": args.requires_approval,
        "status": "proposed",
        "created_at": utc_slug(),
    }
    intents = load_intents()
    intents.append(intent)
    save_intents(intents)
    append_jsonl(LOG_PATH, {"event": "add", **intent})
    record_event("automation.add", actor="harness", status="proposed", **intent)
    print(intent["id"])
    return 0


def scan(_: argparse.Namespace) -> int:
    proposals: list[dict] = []
    if unresolved_reviews():
        proposals.append({
            "kind": "pending-review",
            "title": "Review pending review artifacts",
            "prompt": "Check pending harness review artifacts and summarize unresolved blockers.",
            "cadence": "manual or daily while active",
            "mode": "worktree",
            "risk": "low",
        })
    proposed_skill_files = [
        path for path in (ROOT / "harness" / "proposed-skills").glob("*.md")
        if path.name.lower() != "readme.md"
    ]
    if proposed_skill_files:
        proposals.append({
            "kind": "skill-triage",
            "title": "Triage proposed skills",
            "prompt": "Audit proposed skills for trigger quality, overlap, validation, and promotion readiness.",
            "cadence": "weekly",
            "mode": "worktree",
            "risk": "low",
        })
    if not proposals:
        proposals.append({
            "kind": "weekly-retro",
            "title": "Weekly harness retro",
            "prompt": "Review recent harness telemetry, unresolved risks, reviews, and proposed skills. Report only actionable findings.",
            "cadence": "weekly",
            "mode": "worktree",
            "risk": "low",
        })

    for proposal in proposals:
        print(f"- {proposal['kind']}: {proposal['title']} ({proposal['cadence']})")
    return 0


def unresolved_reviews() -> list[str]:
    review_files = sorted((ROOT / "harness" / "reviews").glob("review-*.md"))
    unresolved = []
    accepted = accepted_review_files()
    for path in review_files:
        rel = str(path.relative_to(ROOT))
        text = path.read_text(encoding="utf-8")
        if rel in accepted:
            continue
        if "Verdict: accept" in text or "Verdict: accept-with-follow-up" in text:
            continue
        unresolved.append(rel)
    prepared = prepared_review_files() - accepted
    unresolved.extend(sorted(prepared - set(unresolved)))
    return unresolved


def prepared_review_files() -> set[str]:
    return review_event_files("review.prepare")


def accepted_review_files() -> set[str]:
    files = set()
    for event in iter_events():
        if event.get("kind") == "review.finalize" and event.get("status") == "accepted":
            review_file = event.get("data", {}).get("review_file")
            if review_file:
                files.add(review_file)
    return files


def review_event_files(kind: str) -> set[str]:
    files = set()
    for event in iter_events():
        if event.get("kind") == kind:
            review_file = event.get("data", {}).get("review_file")
            if review_file:
                files.add(review_file)
    return files


def audit(_: argparse.Namespace) -> int:
    intents = load_intents()
    errors: list[str] = []
    for intent in intents:
        prefix = intent.get("id", "<missing-id>")
        if intent.get("kind") not in ALLOWED_KINDS:
            errors.append(f"{prefix}: invalid kind")
        for key in ["title", "prompt", "cadence", "mode", "risk", "status"]:
            if not intent.get(key):
                errors.append(f"{prefix}: missing {key}")
        if intent.get("risk") == "high" and not intent.get("requires_approval"):
            errors.append(f"{prefix}: high-risk automation requires approval")
        if intent.get("mode") == "local" and intent.get("risk") in {"medium", "high"}:
            errors.append(f"{prefix}: medium/high risk automation should not default to local mode")
    if errors:
        record_event("automation.audit", actor="harness", status="blocked", errors=errors)
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    record_event("automation.audit", actor="harness", status="ok", count=len(intents))
    print("automation intents ok")
    return 0


def list_intents(_: argparse.Namespace) -> int:
    intents = load_intents()
    if not intents:
        print("no automation intents")
        return 0
    for intent in intents:
        print(f"{intent.get('id')}: {intent.get('kind')} {intent.get('status')} - {intent.get('title')}")
    return 0


def render(args: argparse.Namespace) -> int:
    intents = load_intents()
    intent = None
    if args.id:
        intent = next((item for item in intents if item.get("id") == args.id), None)
    elif intents:
        intent = intents[-1]
    if intent is None:
        print("ERROR: automation intent not found", file=sys.stderr)
        return 1

    prompt = f"""Use the Codex Harness automation policy.

Automation kind: {intent.get('kind')}
Title: {intent.get('title')}
Risk: {intent.get('risk')}
Preferred mode: {intent.get('mode')}
Cadence: {intent.get('cadence')}

Task:
{intent.get('prompt')}

Rules:
- Report only actionable findings.
- Do not perform high-risk edits unless explicitly approved.
- If code changes are needed, keep them isolated and run the harness gates before completion.
- If there is nothing to report, say so briefly.
"""
    print(prompt)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    a = sub.add_parser("add")
    a.add_argument("--kind", required=True)
    a.add_argument("--title", required=True)
    a.add_argument("--prompt", required=True)
    a.add_argument("--cadence", default="manual")
    a.add_argument("--mode", choices=["local", "worktree", "cloud"], default="worktree")
    a.add_argument("--risk", choices=["low", "medium", "high"], default="low")
    a.add_argument("--requires-approval", action="store_true")

    sub.add_parser("scan")
    sub.add_parser("audit")
    sub.add_parser("list")
    render_parser = sub.add_parser("render")
    render_parser.add_argument("--id")

    args = parser.parse_args()
    if args.command == "add":
        return add(args)
    if args.command == "scan":
        return scan(args)
    if args.command == "audit":
        return audit(args)
    if args.command == "list":
        return list_intents(args)
    if args.command == "render":
        return render(args)
    raise AssertionError(args.command)


if __name__ == "__main__":
    raise SystemExit(main())
