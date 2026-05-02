# Design Operations

Codex Harness v4 treats UI/UX work as a design-system workflow, not only a code-generation task.

## When To Use

Use the UI/UX workflow when a task changes:

- visual layout
- interaction states
- typography, color, spacing, motion
- page structure
- forms, charts, navigation, dashboards, landing pages
- accessibility or responsive behavior

## Required Artifacts For Normal UI Work

Use these templates under `docs/ai/current/`:

- `templates/UI-UX-Brief.md`
- `templates/Design-System.md`
- `templates/UI-Review.md`

## Recommended Flow

1. Define product type, platform, stack, and primary user goal.
2. Create `UI-UX-Brief.md`.
3. Create or update `Design-System.md`.
4. Implement the smallest useful UI slice.
5. Run browser or screenshot QA when available.
6. Fill `UI-Review.md`.
7. Run `python3 scripts/harness/design_gate.py --ui`.

## Pre-Delivery Checks

- Accessibility: contrast, focus, labels, keyboard, alt text.
- Interaction: hover/focus/active/disabled/loading/error states.
- Responsive: no horizontal scroll, mobile-first layout, readable line lengths.
- Typography/color: semantic tokens, consistent scale, no random raw hex drift.
- Motion: 150-300ms purposeful transitions, reduced-motion support.
- Performance: image dimensions, lazy loading, avoid layout shift.

## Long-Term State

If a project develops a durable visual system, move stable rules into:

```text
harness/design/design-system/MASTER.md
harness/design/design-system/pages/<page>.md
```

Page files should only contain deviations from `MASTER.md`.
