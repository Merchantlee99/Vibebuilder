#!/usr/bin/env python3
"""Single entrypoint for Codex Harness v4 maintenance commands."""

from __future__ import annotations

import argparse
import subprocess
import sys

from common import ROOT


def run(args: list[str]) -> int:
    proc = subprocess.run([sys.executable, *args], cwd=ROOT)
    return proc.returncode


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    check = sub.add_parser("check")
    check.add_argument("--tier", choices=["trivial", "normal", "high-risk"], default="normal")
    check.add_argument("--template", action="store_true")

    close = sub.add_parser("close")
    close.add_argument("--tier", choices=["trivial", "normal", "high-risk"], default="normal")
    close.add_argument("--template", action="store_true")

    classify = sub.add_parser("classify")
    classify.add_argument("text", nargs="+")

    review = sub.add_parser("review")
    review_sub = review.add_subparsers(dest="review_command", required=True)
    prep = review_sub.add_parser("prepare")
    prep.add_argument("--tier", choices=["normal", "high-risk"], default="normal")
    prep.add_argument("--producer", required=True)
    prep.add_argument("--producer-session", default="main")
    prep.add_argument("--reviewer", default="reviewer")
    prep.add_argument("--reviewer-session", default="reviewer-subagent")
    prep.add_argument("--artifact-dir", default="docs/ai/current")
    prep.add_argument("--changed-file", action="append", default=[])
    fin = review_sub.add_parser("finalize")
    fin.add_argument("--review-file")
    fin.add_argument("--changed-file", action="append", default=[])
    fin.add_argument("--allow-unprepared-finalize", action="store_true")
    fin.add_argument("--allow-modified-fingerprint", action="store_true")
    fin.add_argument("--min-section-chars", type=int, default=20)
    fin.add_argument("--hmac-secret-env")
    fin.add_argument("--approval-token")

    subagent = sub.add_parser("subagent")
    subagent_sub = subagent.add_subparsers(dest="subagent_command", required=True)
    sp = subagent_sub.add_parser("plan")
    sp.add_argument("--role", required=True)
    sp.add_argument("--owner", required=True)
    sp.add_argument("--goal", required=True)
    sp.add_argument("--tier", choices=["trivial", "normal", "high-risk"], default="normal")
    sp.add_argument("--mode", choices=["read-only", "workspace-write", "worktree", "cloud"])
    sp.add_argument("--read-scope", action="append", default=[])
    sp.add_argument("--write-scope", action="append", default=[])
    sp.add_argument("--forbidden-path", action="append", default=[])
    sp.add_argument("--stop-condition", default="Return the requested artifact and stop.")
    sp.add_argument("--expected-artifact", default="Concise handoff report.")
    sp.add_argument("--validation", default="State what was checked and what remains unverified.")
    sp.add_argument("--claim", action="store_true")
    sr = subagent_sub.add_parser("release")
    sr.add_argument("--owner", required=True)
    subagent_sub.add_parser("list")
    sc = subagent_sub.add_parser("check")
    sc.add_argument("--quiet", action="store_true")

    score = sub.add_parser("score")
    score.add_argument("--min-score", type=float, default=0)
    score.add_argument("--json", action="store_true")
    metrics = sub.add_parser("metrics")
    metrics.add_argument("--json", action="store_true")
    sub.add_parser("self-test")
    quality = sub.add_parser("quality")
    quality.add_argument("--tier", choices=["trivial", "normal", "high-risk"], default="normal")
    quality.add_argument("--artifact-dir", default="docs/ai/current")
    quality.add_argument("--review-file")
    quality.add_argument("--template", action="store_true")
    quality.add_argument("--json", action="store_true")
    quality.add_argument("--warn-only", action="store_true")

    simplicity = sub.add_parser("simplicity")
    simplicity.add_argument("--artifact-dir", default="docs/ai/current")
    simplicity.add_argument("--file")
    simplicity.add_argument("--template", action="store_true")
    simplicity.add_argument("--required", action="store_true")
    simplicity.add_argument("--json", action="store_true")
    simplicity.add_argument("--warn-only", action="store_true")

    design = sub.add_parser("design")
    design.add_argument("--artifact-dir", default="docs/ai/current")
    design.add_argument("--context", action="append", default=[])
    design.add_argument("--ui", action="store_true")
    design.add_argument("--template", action="store_true")
    design.add_argument("--json", action="store_true")
    design.add_argument("--warn-only", action="store_true")

    events = sub.add_parser("events")
    events_sub = events.add_subparsers(dest="events_command", required=True)
    ev_tail = events_sub.add_parser("tail")
    ev_tail.add_argument("--log", choices=["events", "learnings"], default="events")
    ev_tail.add_argument("--limit", type=int, default=20)
    events_sub.add_parser("verify")
    ev_rotate = events_sub.add_parser("rotate")
    ev_rotate.add_argument("--max-bytes", type=int, default=0)
    ev_rotate.add_argument("--force", action="store_true")

    learning = sub.add_parser("learning")
    learning.add_argument("--threshold", type=int, default=2)
    learning.add_argument("--record", action="store_true")
    learning.add_argument("--json", action="store_true")

    automation = sub.add_parser("automation")
    automation_sub = automation.add_subparsers(dest="automation_command", required=True)
    aa = automation_sub.add_parser("add")
    aa.add_argument("--kind", required=True)
    aa.add_argument("--title", required=True)
    aa.add_argument("--prompt", required=True)
    aa.add_argument("--cadence", default="manual")
    aa.add_argument("--mode", choices=["local", "worktree", "cloud"], default="worktree")
    aa.add_argument("--risk", choices=["low", "medium", "high"], default="low")
    aa.add_argument("--requires-approval", action="store_true")
    automation_sub.add_parser("scan")
    automation_sub.add_parser("audit")
    automation_sub.add_parser("list")
    ar = automation_sub.add_parser("render")
    ar.add_argument("--id")

    skill = sub.add_parser("skill")
    skill_sub = skill.add_subparsers(dest="skill_command", required=True)
    sk_audit = skill_sub.add_parser("audit")
    sk_audit.add_argument("--json", action="store_true")

    index = sub.add_parser("index")
    index_sub = index.add_subparsers(dest="index_command", required=True)
    index_sub.add_parser("rebuild")
    index_sub.add_parser("rebuild-in-place")
    search = index_sub.add_parser("search")
    search.add_argument("query")
    search.add_argument("--limit", type=int, default=10)

    args = parser.parse_args()
    if args.command == "check":
        command = ["scripts/harness/gate.py", "all", "--tier", args.tier]
        if args.template:
            command.append("--template")
        return run(command)
    if args.command == "close":
        command = ["scripts/harness/session_close.py", "--tier", args.tier]
        if args.template:
            command.append("--template")
        return run(command)
    if args.command == "classify":
        return run(["scripts/harness/risk_classifier.py", *args.text])
    if args.command == "review" and args.review_command == "prepare":
        command = [
            "scripts/harness/review_gate.py",
            "prepare",
            "--tier",
            args.tier,
            "--producer",
            args.producer,
            "--producer-session",
            args.producer_session,
            "--reviewer",
            args.reviewer,
            "--reviewer-session",
            args.reviewer_session,
            "--artifact-dir",
            args.artifact_dir,
        ]
        for changed in args.changed_file:
            command.extend(["--changed-file", changed])
        return run(command)
    if args.command == "review" and args.review_command == "finalize":
        command = ["scripts/harness/review_gate.py", "finalize"]
        if args.review_file:
            command.extend(["--review-file", args.review_file])
        for changed in args.changed_file:
            command.extend(["--changed-file", changed])
        if not args.allow_unprepared_finalize:
            command.append("--require-prepared-event")
        if args.allow_modified_fingerprint:
            command.append("--allow-modified-fingerprint")
        if args.min_section_chars:
            command.extend(["--min-section-chars", str(args.min_section_chars)])
        if args.hmac_secret_env:
            command.extend(["--hmac-secret-env", args.hmac_secret_env])
        if args.approval_token:
            command.extend(["--approval-token", args.approval_token])
        return run(command)
    if args.command == "subagent" and args.subagent_command == "plan":
        command = [
            "scripts/harness/subagent_planner.py",
            "plan",
            "--role",
            args.role,
            "--owner",
            args.owner,
            "--goal",
            args.goal,
            "--tier",
            args.tier,
        ]
        if args.mode:
            command.extend(["--mode", args.mode])
        for value in args.read_scope:
            command.extend(["--read-scope", value])
        for value in args.write_scope:
            command.extend(["--write-scope", value])
        for value in args.forbidden_path:
            command.extend(["--forbidden-path", value])
        command.extend(["--stop-condition", args.stop_condition])
        command.extend(["--expected-artifact", args.expected_artifact])
        command.extend(["--validation", args.validation])
        if args.claim:
            command.append("--claim")
        return run(command)
    if args.command == "subagent" and args.subagent_command == "release":
        return run(["scripts/harness/subagent_planner.py", "release", "--owner", args.owner])
    if args.command == "subagent" and args.subagent_command == "list":
        return run(["scripts/harness/subagent_planner.py", "list"])
    if args.command == "subagent" and args.subagent_command == "check":
        command = ["scripts/harness/subagent_planner.py", "check"]
        if args.quiet:
            command.append("--quiet")
        return run(command)
    if args.command == "score":
        command = ["scripts/harness/score.py"]
        if args.min_score:
            command.extend(["--min-score", str(args.min_score)])
        if args.json:
            command.append("--json")
        return run(command)
    if args.command == "metrics":
        command = ["scripts/harness/ops_metrics.py"]
        if args.json:
            command.append("--json")
        return run(command)
    if args.command == "self-test":
        return run(["scripts/harness/self_test.py"])
    if args.command == "quality":
        command = ["scripts/harness/quality_gate.py", "--tier", args.tier, "--artifact-dir", args.artifact_dir]
        if args.review_file:
            command.extend(["--review-file", args.review_file])
        if args.template:
            command.append("--template")
        if args.json:
            command.append("--json")
        if args.warn_only:
            command.append("--warn-only")
        return run(command)
    if args.command == "simplicity":
        command = ["scripts/harness/simplicity_gate.py", "--artifact-dir", args.artifact_dir]
        if args.file:
            command.extend(["--file", args.file])
        if args.template:
            command.append("--template")
        if args.required:
            command.append("--required")
        if args.json:
            command.append("--json")
        if args.warn_only:
            command.append("--warn-only")
        return run(command)
    if args.command == "design":
        command = ["scripts/harness/design_gate.py", "--artifact-dir", args.artifact_dir]
        for value in args.context:
            command.extend(["--context", value])
        if args.ui:
            command.append("--ui")
        if args.template:
            command.append("--template")
        if args.json:
            command.append("--json")
        if args.warn_only:
            command.append("--warn-only")
        return run(command)
    if args.command == "events" and args.events_command == "tail":
        return run(["scripts/harness/event_log.py", "tail", "--log", args.log, "--limit", str(args.limit)])
    if args.command == "events" and args.events_command == "verify":
        return run(["scripts/harness/event_log.py", "verify"])
    if args.command == "events" and args.events_command == "rotate":
        command = ["scripts/harness/event_log.py", "rotate"]
        if args.max_bytes:
            command.extend(["--max-bytes", str(args.max_bytes)])
        if args.force:
            command.append("--force")
        return run(command)
    if args.command == "learning":
        command = ["scripts/harness/learning_detector.py", "--threshold", str(args.threshold)]
        if args.record:
            command.append("--record")
        if args.json:
            command.append("--json")
        return run(command)
    if args.command == "automation" and args.automation_command == "add":
        command = [
            "scripts/harness/automation_planner.py",
            "add",
            "--kind",
            args.kind,
            "--title",
            args.title,
            "--prompt",
            args.prompt,
            "--cadence",
            args.cadence,
            "--mode",
            args.mode,
            "--risk",
            args.risk,
        ]
        if args.requires_approval:
            command.append("--requires-approval")
        return run(command)
    if args.command == "automation" and args.automation_command == "scan":
        return run(["scripts/harness/automation_planner.py", "scan"])
    if args.command == "automation" and args.automation_command == "audit":
        return run(["scripts/harness/automation_planner.py", "audit"])
    if args.command == "automation" and args.automation_command == "list":
        return run(["scripts/harness/automation_planner.py", "list"])
    if args.command == "automation" and args.automation_command == "render":
        command = ["scripts/harness/automation_planner.py", "render"]
        if args.id:
            command.extend(["--id", args.id])
        return run(command)
    if args.command == "skill" and args.skill_command == "audit":
        command = ["scripts/harness/skillify_audit.py", "all"]
        if args.json:
            command.append("--json")
        return run(command)
    if args.command == "index" and args.index_command == "rebuild":
        return run(["scripts/harness/session_index.py", "rebuild"])
    if args.command == "index" and args.index_command == "rebuild-in-place":
        return run(["scripts/harness/session_index.py", "rebuild-in-place"])
    if args.command == "index" and args.index_command == "search":
        return run(["scripts/harness/session_index.py", "search", args.query, "--limit", str(args.limit)])
    raise AssertionError(args.command)


if __name__ == "__main__":
    raise SystemExit(main())
