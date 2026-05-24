---
name: visual-review
description: Use for independent review of UI screenshots, layout maps, CSS/static frontend inventories, information density, customer language, responsive quality, and destructive-action clarity. Do not use as a substitute for tests or implementation review.
---

# Visual Review

Review evidence from the user's perspective.

## Checks

- Can the user understand the current state in three seconds?
- Is the primary action visible, safe, and reachable?
- Are dangerous actions visually unambiguous?
- Is density appropriate for the workflow?
- Are customer-facing terms understandable?
- Are error/empty/loading states designed, not abandoned?
- Does the implementation follow the existing component and token system?

## Output Contract

Return blockers, warnings, evidence reviewed, missing states, and residual risk.
