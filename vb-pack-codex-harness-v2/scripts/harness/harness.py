#!/usr/bin/env python3
"""Single entrypoint for Codex Harness v2 maintenance commands."""

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
    fin = review_sub.add_parser("finalize")
    fin.add_argument("--review-file")

    subagent = sub.add_parser("subagent")
    subagent_sub = subagent.add_subparsers(dest="subagent_command", required=True)
    subagent_sub.add_parser("check")

    sub.add_parser("score")
    sub.add_parser("metrics")
    sub.add_parser("self-test")
    sub.add_parser("quality")
    sub.add_parser("events")
    sub.add_parser("learning")

    automation = sub.add_parser("automation")
    automation_sub = automation.add_subparsers(dest="automation_command", required=True)
    automation_sub.add_parser("scan")
    automation_sub.add_parser("audit")

    skill = sub.add_parser("skill")
    skill_sub = skill.add_subparsers(dest="skill_command", required=True)
    skill_sub.add_parser("audit")

    index = sub.add_parser("index")
    index_sub = index.add_subparsers(dest="index_command", required=True)
    index_sub.add_parser("rebuild")
    search = index_sub.add_parser("search")
    search.add_argument("query")

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
        return run([
            "scripts/harness/review_gate.py",
            "prepare",
            "--tier",
            args.tier,
            "--producer",
            args.producer,
            "--producer-session",
            args.producer_session,
        ])
    if args.command == "review" and args.review_command == "finalize":
        command = ["scripts/harness/review_gate.py", "finalize", "--require-prepared-event"]
        if args.review_file:
            command.extend(["--review-file", args.review_file])
        return run(command)
    if args.command == "subagent" and args.subagent_command == "check":
        return run(["scripts/harness/subagent_planner.py", "check"])
    if args.command == "score":
        return run(["scripts/harness/score.py"])
    if args.command == "metrics":
        return run(["scripts/harness/ops_metrics.py"])
    if args.command == "self-test":
        return run(["scripts/harness/self_test.py"])
    if args.command == "quality":
        return run(["scripts/harness/quality_gate.py", "--tier", "high-risk", "--template"])
    if args.command == "events":
        return run(["scripts/harness/event_log.py", "tail", "--log", "events"])
    if args.command == "learning":
        return run(["scripts/harness/learning_detector.py"])
    if args.command == "automation" and args.automation_command == "scan":
        return run(["scripts/harness/automation_planner.py", "scan"])
    if args.command == "automation" and args.automation_command == "audit":
        return run(["scripts/harness/automation_planner.py", "audit"])
    if args.command == "skill" and args.skill_command == "audit":
        return run(["scripts/harness/skillify_audit.py", "all"])
    if args.command == "index" and args.index_command == "rebuild":
        return run(["scripts/harness/session_index.py", "rebuild"])
    if args.command == "index" and args.index_command == "search":
        return run(["scripts/harness/session_index.py", "search", args.query])
    raise AssertionError(args.command)


if __name__ == "__main__":
    raise SystemExit(main())
