# AGENTS.md

## Purpose

This repository is a Codex-only v5 harness template for implementation-first product and software development. It preserves v2 implementation discipline, v3 high-risk strictness, and v4 simplicity/UI discipline, then adds task-profile routing, evidence gates, UI runtime proof, static frontend analysis, and audited Hermes-style self-improvement.

## Operating Contract

- The main Codex session is the orchestrator.
- Classify work before meaningful edits with a task profile: `kind`, `tier`, `surface`, `changed_paths`, required gates, UI evidence status, strict status, and residual risk.
- Do not treat this template as an activated production project unless `harness/runtime.json` says `deployment_profile` is `project`.
- Heavy visual, strict, browser, subagent, or learning workflows activate only when the task profile justifies them.
- Coding correctness outranks visual QA.
- Scripts validate objective evidence and policy shape. They do not decide architecture, taste, or product correctness.

## Tier Rules

- `trivial`: one small low-risk change. Main Codex can work directly and validate briefly.
- `normal`: meaningful behavior change, multiple files, unclear implementation path, or user-facing output. Requires plan, validation evidence, and independent review before completion.
- `high-risk`: auth, payments, security, data migration, infra, destructive actions, broad refactor, legal/compliance, or ambiguous blast radius. Requires strict evidence, rollback plan, independent review, and explicit risk validation.

High-risk routing overrides UI routing. A high-risk UI is handled as high-risk first and UI second.

## Evidence Rules

- Do not report completion for `normal+` work without implementation evidence.
- Screenshot-only completion is forbidden for `normal+` UI work.
- UI evidence is required when rendered behavior, layout, interaction, or user-facing state changes.
- UI evidence can be not applicable only with `not_applicable_reason` and `residual_risk`.
- Sensitive screens need redacted screenshots or an explicit no-screenshot rationale.
- Non-web UI must use adapter/manual evidence instead of failing only because browser evidence is unavailable.
- Evidence records belong in `harness/evidence/evidence.jsonl`; artifacts belong in `harness/evidence/artifacts/`.

## Subagent Rules

- Spawn subagents only for bounded parallel work that reduces wall-clock time, context noise, or risk.
- Do not delegate the immediate blocking step if the parent must act on it right now.
- No producer self-review.
- Subagent output is evidence, not final decision.
- Writing agents need explicit write scope, stop condition, and ownership.
- Max depth is 1 unless the user explicitly asks for recursive delegation.
- The orchestrator owns final synthesis and completion.

## Preferred Agent Roles

- `pm_strategist`: product framing, PRD, acceptance criteria, metrics, scope.
- `pm_redteam`: attacks product assumptions, weak success metrics, and scope creep.
- `docs_researcher`: verifies APIs and version-specific behavior from primary docs.
- `code_mapper`: maps code paths before edits.
- `task_distributor`: splits broad work into disjoint ownership scopes.
- `reviewer`: independent correctness, regression, security, and test review.
- `security_auditor`: high-risk security and sensitive data review.
- `browser_qa`: browser/runtime reproduction and state verification.
- `visual_reviewer`: screenshot, layout, density, hierarchy, responsive, and customer-language review.
- `learning_curator`: repeated failure clustering and proposed improvement review.

## Native Feature Policy

- Use terminal for deterministic checks, search, tests, and scripts.
- Use browser or Playwright when rendered UI behavior matters.
- Use built-in Git tools for diff, staged changes, commits, and review comments; use terminal for advanced Git.
- Use computer use only for GUI-only tasks or flows that cannot be completed through terminal/browser/plugin surfaces.
- Use automations only for long waits, recurring audits, stale reviews, weekly retros, and skill triage. Do not create unattended high-risk automations without explicit user approval.

## Completion Rules

- Use `scripts/harness/task_profile_gate.py check --profile <file>` for `normal+` work when a profile artifact exists.
- Use `scripts/harness/implementation_gate.py` for `normal+` implementation evidence.
- Use `scripts/harness/ui_evidence_gate.py` when UI evidence is required.
- Use `scripts/harness/runtime_evidence_gate.py` for runtime/debug or rendered frontend behavior.
- Use `scripts/harness/non_web_ui_evidence_gate.py` for native, desktop, mobile, CLI TUI, or other non-browser UI.
- Use `scripts/harness/memory_guard.py audit` before promoting repeated learnings into active rules.
- Use `scripts/harness/benchmark_harness.py --quick` before tightening gates that could slow normal coding tasks.
- Continue using v2/v3/v4 gates: review, quality, simplicity, design, subagent, session close, strict review for high-risk work.
- If a gate fails, fix the issue or report the blocker plainly.

## File Boundaries

- Keep static Codex control-plane files under `.codex/`.
- Keep repo skills under `.agents/skills/`.
- Keep mutable runtime, evidence, reviews, telemetry, audits, memory, and proposed skills under `harness/`.
- Keep durable AI project notes under `docs/ai/`.

## Safety

- Never run destructive Git commands unless explicitly requested.
- Do not modify external reference repositories or user source documents while working on this template.
- Treat official documentation as the source of truth for Codex behavior.
- Do not allow raw learning logs to become active rules without curation, review, and explicit promotion.

## Evolution Rules

- Use `scripts/harness/automation_planner.py audit` before relying on automation intents.
- Use `scripts/harness/skillify_audit.py all` before promoting proposed skills into `.agents/skills`.
- Use `scripts/harness/memory_guard.py audit` before memory/policy promotion.
- Use `scripts/harness/score.py --min-score 95` to check whether this harness still meets the target operating standard.
- Use `scripts/harness/event_log.py tail` and `scripts/harness/session_index.py search` when reconstructing prior work.
