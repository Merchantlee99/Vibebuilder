# Ethos

Codex Harness v3 optimizes for high-trust long-running work, not prompt ceremony.

## Principles

- Natural language first: users should describe outcomes, not remember command names.
- Native before custom: prefer Codex-supported project instructions, skills, subagents, worktrees, terminal, browser, and automations.
- Thin core, strong gates: keep always-loaded instructions short and move details into skills and scripts.
- Evidence over confidence: plans, validation, reviews, and residual risk matter more than fluent completion claims.
- Read-only before write: use planning and mapping agents to reduce uncertainty before editing.
- Worktree before collision: isolate broad or risky implementation work.
- Review independence: producers do not approve their own work.
- Human-in-the-loop evolution: repeated failures can propose skills, but promotion requires audit and approval.
- Strict when it matters: high-risk work should trade some speed for stronger review identity, telemetry, and completion gates.

## What This Avoids

- Large monolithic prompt files that rot.
- Unbounded auto-spawn agent swarms.
- Reviewer theater with no concrete evidence.
- Hidden mutable state under `.codex`.
- Relying on experimental hooks as the only enforcement mechanism.
- Automatic self-modification of the framework without a proposed-skill review path.
- Pretending local guardrails prove external human approval or off-site backup.
