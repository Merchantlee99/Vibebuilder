---
name: plan-before-change
description: Use when making normal or high-risk code changes that need an implementation plan. Creates a concise plan with ownership, validation, rollback, and subagent dispatch criteria.
---

# Plan Before Change

Use this before editing files for `normal` or `high-risk` work.

## Steps

1. Inspect relevant files before proposing implementation.
2. If ownership is unclear, use or request a `code_mapper` subagent.
3. If work is broad, use or request `task_distributor`.
4. Define slices with explicit write scopes.
5. Define validation commands and expected outcomes.
6. Define rollback or recovery.
7. Identify whether independent review is required.

## Plan Shape

```text
Goal:
Tier:
Scope:
Non-goals:
Owned paths:
Subagents:
Implementation slices:
Validation:
Rollback:
Review:
Open risks:
```

Do not over-plan trivial work.

## Non-Trigger

Do not use for tiny one-file edits with obvious validation unless the user asks for planning.
