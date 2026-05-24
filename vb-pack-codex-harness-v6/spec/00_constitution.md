# v6 Constitution

## Source Of Truth

- `docs/` explains context, history, and operational notes.
- `spec/` governs accepted product and system behavior.
- Accepted specs are standards, not snapshots of current implementation.
- If code and accepted spec diverge, classify the gap instead of weakening the spec to match incomplete code.

## Natural-Language Routing

- Normal+ work must produce an intent routing artifact before completion.
- The route decides which spec, domain, evidence, UI, runtime, strict, and team-rule gates are needed.
- AI may choose the route, but deterministic gates must verify the route artifact.

## Team Rules

- Team conventions inferred from code, docs, PRs, reviews, or tests are proposals until reviewed.
- High-risk, security, billing, auth, deletion, DB migration, public API, AGENTS.md always-rule, and global design-system rules cannot be silently promoted.
