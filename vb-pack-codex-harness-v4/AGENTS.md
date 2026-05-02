# AGENTS.md

## Purpose

This repository is a Codex-only v4 harness template for natural-language product and software development work with simplicity discipline and UI/UX design intelligence.

## Operating Contract

- The main Codex session is the orchestrator.
- The user may give only natural-language instructions.
- Codex should classify work as `trivial`, `normal`, or `high-risk` before meaningful edits.
- Codex may use subagents, terminal, built-in Git tools, browser, worktrees, cloud mode, automations, and computer use when the harness rules justify them.
- Do not treat this template as an activated production project unless `harness/runtime.json` says `deployment_profile` is `project`.
- Treat v4 as a creative-daily harness: use v2's stability, add Karpathy-style simplicity checks, and invoke UI/UX design workflows when interface quality matters.

## Tier Rules

- `trivial`: one small low-risk change. Main Codex can work directly and validate briefly.
- `normal`: meaningful behavior change, multiple files, unclear implementation path, or user-facing output. Requires plan, validation, and independent review before completion.
- `high-risk`: auth, payments, security, data migration, infra, destructive actions, broad refactor, legal/compliance, or ambiguous blast radius. Requires product/technical red-team, rollback plan, independent review, and explicit validation evidence.

## Subagent Rules

- Spawn subagents only when useful for bounded parallel work.
- Do not delegate the immediate blocking step if the parent must act on it right now.
- Read-only subagents may fan out for planning, research, mapping, and review.
- Writing agents need explicit write scope, stop condition, and ownership.
- Prefer worktree mode for worker agents, broad changes, and risky edits.
- The orchestrator remains responsible for final synthesis and completion.

## Preferred Agent Roles

- `pm_strategist`: product framing, PRD, acceptance criteria, metrics, scope.
- `pm_redteam`: attacks product assumptions, weak success metrics, and scope creep.
- `docs_researcher`: verifies APIs and version-specific behavior from primary docs.
- `code_mapper`: maps code paths before edits.
- `task_distributor`: splits broad work into disjoint ownership scopes.
- `reviewer`: independent correctness, regression, security, and test review.
- `security_auditor`: high-risk security and sensitive data review.
- `browser_debugger`: UI/browser reproduction and QA when terminal checks are insufficient.
- `karpathy-engineering` skill: assumptions, simplicity, surgical changes, and verifiable success criteria.
- `ui-ux-design` skill: design system, accessibility, responsive behavior, interaction states, and UI anti-pattern review.

## Native Feature Policy

- Use terminal for deterministic checks, search, tests, and scripts.
- Use built-in Git tools for diff, staged changes, commits, and review comments; use terminal for advanced Git.
- Use browser for current docs, linked issues, release notes, and web UI QA.
- Use computer use only for GUI-only tasks or flows that cannot be completed through terminal/browser/plugin surfaces.
- Use automations for long waits, recurring audits, stale reviews, weekly retros, and skill triage. Do not create unattended high-risk automations without explicit user approval.

## Completion Rules

- Do not report completion for `normal+` work without validation evidence.
- Do not self-approve `normal+` work. The reviewer must be independent from the producer.
- Use `scripts/harness/review_gate.py prepare` and `finalize` for review artifacts when the task is `normal+`.
- Use `scripts/harness/subagent_planner.py plan --claim` before assigning write-scoped worker subagents.
- Use `scripts/harness/session_close.py` before final completion when project artifacts exist.
- Use `scripts/harness/quality_gate.py` for `normal+` work and treat high-risk quality failures as blockers.
- Use `scripts/harness/simplicity_gate.py` for non-trivial implementation work when overengineering or broad edits are a risk.
- Use `scripts/harness/design_gate.py` when UI/UX artifacts or frontend visual changes are in scope.
- Record residual risks and follow-ups when validation is incomplete.
- If a gate fails, fix the issue or report the blocker plainly.

## File Boundaries

- Keep static Codex control-plane files under `.codex/`.
- Keep repo skills under `.agents/skills/`.
- Keep mutable runtime, reviews, telemetry, audits, and proposed skills under `harness/`.
- Keep durable AI project notes under `docs/ai/`.

## Safety

- Never run destructive Git commands unless explicitly requested.
- Do not modify external reference repositories or user source documents while working on this template.
- Treat official documentation as the source of truth for Codex behavior.

## Evolution Rules

- Use `scripts/harness/automation_planner.py audit` before relying on automation intents.
- Use `scripts/harness/skillify_audit.py all` before promoting proposed skills into `.agents/skills`.
- Use `scripts/harness/score.py --min-score 95` to check whether this harness still meets the target operating standard.
- Use `scripts/harness/event_log.py tail` and `scripts/harness/session_index.py search` when reconstructing prior work.
