---
name: ui-evidence
description: Use when rendered UI behavior, layout, interaction states, responsive behavior, accessibility, customer language, or user-facing state changes. Do not use for pure backend, docs, or non-rendered refactors.
---

# UI Evidence

UI evidence is an overlay on implementation validation, not a replacement.

## Required For Normal+ UI Work

1. Screenshot or platform visual artifact with route, state, and viewport.
2. At least one non-screenshot evidence item: layout, accessibility, runtime, static frontend audit, or independent UI review.
3. State coverage notes for default, loading, empty, error, success, disabled, hover/focus, or permission states as applicable.
4. Sensitive-screen redaction or no-screenshot rationale.
5. Residual risk.

## Output Contract

Return:

- route/state/viewport matrix
- screenshot artifact paths
- DOM/layout/CSS/accessibility evidence
- blockers and warnings
- customer-language notes
- residual risk

Do not say a UI is improved without visual or runtime evidence.
