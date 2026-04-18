# AGENTS.md

## Purpose

This repository uses a Codex-native harness optimized for long-running software work inside the Codex app.

## Default Operating Model

- The main Codex session is the orchestrator.
- Non-trivial work must be grounded in `Prompt.md`, `PRD.md`, `Plan.md`, `Implement.md`, and `Documentation.md`.
- `Subagent-Manifest.md` is required for `normal` and `high-risk` work.
- Long-term memory lives in files and telemetry, not chat alone.

## Capability Router

- Use `subagents` for bounded parallel codebase questions or disjoint implementation slices.
- Use `automations` for follow-ups that should wake this thread later, recurring audits, and weekly retros.
- Use built-in git tools first for status, diff, log, and review state.
- Use the integrated terminal for reproducible setup, search, tests, and debugging.
- Use the in-app browser for current docs, linked issues, source-cited research, and browser QA.
- Escalate to computer use only when browser or terminal cannot complete auth, local-app, or complex GUI work.

## Modes

- `local`: planning, orchestration, secrets, small fixes, existing dirty worktree.
- `worktree`: default for worker subagents, risky edits, refactors, and parallel implementation.
- `cloud`: clean-room validation, isolated reproduction, and read-heavy review. Do not rely on local secrets.
- Template repositories stay in `advisory` mode; only copied project instances should adopt `project` profile and consider `enforced`.

## Delivery Tiers

- `trivial`: <= 20 LOC, 1 file, low blast radius.
- `normal`: multiple edits or meaningful behavior change. Requires plan and validation.
- `high-risk`: auth, payments, migrations, infra, broad refactors, or unclear blast radius. Requires options, rollback, and independent review.

## Required Artifacts

- `Prompt.md`: goal, constraints, done-when.
- `PRD.md`: user problem, flows, acceptance criteria, risks.
- `Plan.md`: milestones, slices, validation, rollback.
- `Implement.md`: current slice, owned paths, commands, findings.
- `Documentation.md`: decisions, known gaps, restart point.
- `Subagent-Manifest.md`: role ownership, mode, write scope, stop condition.
- `Automation-Intent.md`: automation strategy and follow-up contract when the task spans time.

## Subagent Rules

- Do not delegate the immediate blocking step if the main session needs that result now.
- `explorer` subagents answer a specific codebase question and do not edit production files.
- `worker` subagents own explicit write paths and default to `worktree`.
- `reviewer` subagents do not edit the same production scope they review.
- One write path can have one active owner at a time.
- Waiting is sparse. The orchestrator should keep moving on non-overlapping work.
- Preferred workflow: `python3 scripts/harness/subagent_planner.py plan --role <role> --owner <owner> --goal "<goal>" ...` before launching a real subagent.

## Review Rules

- `normal` and `high-risk` work require an independent review outcome before completion.
- Reviews focus on bugs, regressions, missing tests, blast radius, and rollback readiness.
- Reviews should cite affected files and the validation actually run.
- Review files must declare `Reviewer`, `Producer`, `Reviewer-Session`, and `Producer-Session`.
- `Reviewer` must differ from `Producer`, and review session must differ from producer session.
- Preferred workflow: `python3 scripts/harness/review_gate.py prepare --tier <tier>` before requesting review, then `python3 scripts/harness/review_gate.py finalize --tier <tier>` before completion.
- A reviewer can write review artifacts under `.codex/reviews/` but should not silently patch the same scope.

## Automation Rules

- Prefer thread heartbeats for follow-ups in the same project conversation.
- Create automations for weekly retros, stale-task checks, pending audit reminders, or waiting states longer than one day.
- Automation prompts describe the task, not the schedule.
- Preferred workflow: `python3 scripts/harness/automation_planner.py scan` before creating a real automation.

## Feedback Loop

- Use `python3 scripts/harness/memory_feedback.py prefetch "<task>"` before complex work when prior learnings may matter.
- Use `python3 scripts/harness/memory_feedback.py sync-from-events` after repeated failures or blocked work.
- Use `python3 scripts/harness/skill_auto_gen.py` when repeated learning patterns accumulate.
- Use `python3 scripts/harness/insights_report.py` for periodic retros and audit material.
- Use `python3 scripts/harness/activity_bridge.py sync` when you need an explicit telemetry sync outside the normal gates.

## Git Rules

- Prefer built-in git tools for inspection, then terminal if needed.
- Keep one logical change per commit.
- Do not use destructive git commands unless the user explicitly asks.

## Browser and Computer Use

- Browser first for docs, issue context, release notes, and browser QA.
- Computer use is reserved for GUI-only flows, auth obstacles, or desktop-app interaction.

## Completion Checklist

- Scope matches `Plan.md`.
- Validation is recorded in `Implement.md`.
- Decisions and restart point are updated in `Documentation.md`.
- Required review is complete for `normal+`.
- Review artifact includes independent reviewer metadata.
- `Automation-Intent.md` and `.codex/context/automation-intents.json` reflect the follow-up plan when the task spans time.
