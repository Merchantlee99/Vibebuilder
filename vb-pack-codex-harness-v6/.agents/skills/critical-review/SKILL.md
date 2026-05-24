---
name: critical-review
description: Use when reviewing a plan, PRD, implementation, diff, or completion claim. Focuses on correctness, regressions, missing tests, and risk rather than style.
---

# Critical Review

Review as an independent risk reducer.

## Review Priority

1. Correctness bugs.
2. User-visible behavior regressions.
3. Security, privacy, and data integrity risk.
4. Missing tests or weak validation.
5. Rollback and operational risk.
6. Maintainability only when it affects future correctness.

## Findings

Each finding should include:

- severity
- evidence
- affected file or behavior
- why it matters
- smallest recommended fix

If there are no findings, say that explicitly and list residual risks or verification gaps.

Do not dilute the review with style-only comments unless asked.

