# Ethos

Codex Harness v4 optimizes for reliable long-running work, simple engineering, and high-quality UI/UX without prompt ceremony.

## Principles

- Natural language first: users should describe outcomes, not remember command names.
- Native before custom: prefer Codex-supported project instructions, skills, subagents, worktrees, terminal, browser, and automations.
- Thin core, strong gates: keep always-loaded instructions short and move details into skills and scripts.
- Evidence over confidence: plans, validation, reviews, and residual risk matter more than fluent completion claims.
- Read-only before write: use planning and mapping agents to reduce uncertainty before editing.
- Worktree before collision: isolate broad or risky implementation work.
- Review independence: producers do not approve their own work.
- Human-in-the-loop evolution: repeated failures can propose skills, but promotion requires audit and approval.
- Simplicity as leverage: avoid speculative abstractions and broad changes unless the current task proves they are needed.
- Design as a system: UI work needs tokens, hierarchy, accessibility, and interaction states before visual polish.

## What This Avoids

- Large monolithic prompt files that rot.
- Unbounded auto-spawn agent swarms.
- Reviewer theater with no concrete evidence.
- Hidden mutable state under `.codex`.
- Relying on experimental hooks as the only enforcement mechanism.
- Automatic self-modification of the framework without a proposed-skill review path.
- Generic AI-looking interfaces with no product-specific design direction.
- Large refactors that cannot be traced to the user's request.
