# Ethos

Codex Harness v6 optimizes for natural-language intent routing, shared domain language, spec-governed implementation, evidence-backed completion, and reviewed team-rule evolution without prompt ceremony.

## Principles

- Natural language first: users should describe outcomes, not remember command names.
- Native before custom: prefer Codex-supported project instructions, skills, subagents, worktrees, terminal, browser, and automations.
- Thin core, strong gates: keep always-loaded instructions short and move details into skills and scripts.
- Route before acting: normal+ natural-language work needs a recorded route before completion.
- Spec governs: narrative docs explain, accepted specs define product and system promises.
- Evidence over confidence: plans, implementation proof, runtime/UI evidence, reviews, and residual risk matter more than fluent completion claims.
- Read-only before write: use planning and mapping agents to reduce uncertainty before editing.
- Worktree before collision: isolate broad or risky implementation work.
- Review independence: producers do not approve their own work.
- Human-in-the-loop evolution: repeated failures can propose skills, but promotion requires audit and approval.
- Team-rule proposals before promotion: inferred conventions are reviewed artifacts, not automatic always rules.
- Simplicity as leverage: avoid speculative abstractions and broad changes unless the current task proves they are needed.
- Design as a system: UI work needs tokens, hierarchy, accessibility, and interaction states before visual polish.

## What This Avoids

- Large monolithic prompt files that rot.
- Unbounded auto-spawn agent swarms.
- Reviewer theater with no concrete evidence.
- Smart-sounding routing decisions that are not recorded.
- Specs downgraded to match incomplete code.
- Hidden mutable state under `.codex`.
- Relying on experimental hooks as the only enforcement mechanism.
- Automatic self-modification of the framework without a proposed-skill review path.
- Automatic promotion of inferred team rules without evidence, collision review, and approval.
- Generic AI-looking interfaces with no product-specific design direction.
- Large refactors that cannot be traced to the user's request.
