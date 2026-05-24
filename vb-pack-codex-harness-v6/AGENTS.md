# AGENTS.md

## Purpose

This repository is a Codex-only v6 harness template for natural-language intent-routed product and software development. It preserves v2 implementation discipline, v3 high-risk strictness, v4 simplicity/UI discipline, and v5 implementation/UI/runtime evidence, then adds grill-style intent elicitation, domain language, L0-L3 specs, REQ evidence mapping, spec drift review, and reviewed team-rule mining.

## Operating Contract

- The main Codex session is the orchestrator.
- Route normal+ natural-language work before meaningful edits with `Intent-Routing.json`: mode, tier, grill path, spec layers, required gates, team-rule scan, routing reason, and completion rule.
- Keep `Task-Profile.json` for implementation/evidence details after the intent route is selected.
- Do not treat this template as an activated production project unless `harness/runtime.json` says `deployment_profile` is `project`.
- Heavy visual, strict, browser, subagent, spec, or learning workflows activate only when the intent route justifies them.
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

## Intent Spec Rules

- `docs/` explains. `spec/` governs.
- For behavior changes, keep intent in `spec/` or the active spec artifact and keep narrative explanation in `docs/`.
- Before implementing accepted behavior, list the governing `REQ-...` or `REQ-...:Sx` IDs and the verification obligation for each touched statement.
- Shared nouns, states, IDs, ownership, scope, or authority require a domain-truth section before code relies on them.
- Async work, external AI, ingestion, auth, deletion, privacy, retry, rollback, idempotency, partial failure, or external integrations require interface-contract coverage.
- Generated test stubs, planned evidence rows, and `@Spec(...)` traces are not completion evidence until a real test, guardrail, smoke check, or named manual record has executed.
- Do not weaken an accepted spec to match incomplete code. Classify the mismatch as `missing_implementation`, `partial_implementation`, `missing_test`, `wrong_code`, `wrong_spec`, or `decision_gap`.
- Do not claim `complete`, `ready`, or `done` for broad work until the selected task mode's completion rule is satisfied.

## Grill And Team-Rule Routing

- Use `grill-me` for early ideas, unclear intent, or work without a codebase-backed shared language.
- Use `grill-with-docs` when code, docs, specs, ADRs, tests, reviews, or team traces already exist.
- Existing team behavior can become a `Team-Rule-Proposal.md`, but it is not active until reviewed and promoted.
- Never silently promote inferred rules into `AGENTS.md`, strict policy, security policy, billing/auth/deletion behavior, public API contracts, DB migration rules, or global design-system rules.

## GitHub And Release Rules

- For every `normal+` change, inspect Git state before final reporting: branch, dirty files, staged files, and relevant diff.
- Keep one logical change per commit. Do not commit, push, tag, publish a release, or open a PR unless the user requested it or the project policy explicitly allows it.
- Use `templates/GitHub-Release.md` whenever a task affects versioning, public behavior, packaging, installation, migration, CLI/API contract, release notes, or deployment.
- Release-impact labels require all four checks: authoritative requirement, target release scope, implementation evidence, and core-journey impact.
- A release candidate must have version source of truth, changelog/release notes, validation evidence, rollback path, and independent review.
- Release publication order is: update version metadata, update changelog/release notes, run checks, commit, push branch, create or update PR, tag `v<version>`, publish GitHub release from that tag.
- If checks fail, do not tag. If tagging succeeds but GitHub release publication fails, retry publication from the existing tag instead of moving the tag.

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

- Use `scripts/harness/intent_router_gate.py` for `normal+` work before final completion.
- Use `scripts/harness/domain_language_gate.py` when shared nouns, states, IDs, ownership, authority, or UI vocabulary change.
- Use `scripts/harness/spec_gate.py` for L1/L2/L3 spec validation when behavior changes.
- Use `scripts/harness/req_evidence_gate.py` before claiming accepted REQ statements are complete.
- Use `scripts/harness/team_rule_mining_gate.py` and `scripts/harness/rule_promotion_gate.py` before team rules become active.
- Use `scripts/harness/spec_drift_gate.py` when reviewing accepted spec against code/evidence.
- Use `scripts/harness/task_profile_gate.py check --profile <file>` for `normal+` work when a profile artifact exists.
- Use `scripts/harness/implementation_gate.py` for `normal+` implementation evidence.
- Use `scripts/harness/ui_evidence_gate.py` when UI evidence is required.
- Use `scripts/harness/runtime_evidence_gate.py` for runtime/debug or rendered frontend behavior.
- Use `scripts/harness/non_web_ui_evidence_gate.py` for native, desktop, mobile, CLI TUI, or other non-browser UI.
- Use `scripts/harness/release_gate.py --template` for template release readiness, and project mode before release candidates or publication.
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
