# Design Operations

Codex Harness v5 treats UI/UX work as an evidence-backed design workflow, not only a code-generation task.

## When To Use

Use the UI evidence workflow when a task changes:

- visual layout
- interaction states
- typography, color, spacing, motion
- page structure
- forms, charts, navigation, dashboards, landing pages
- accessibility or responsive behavior
- route/state/viewport behavior
- sensitive or destructive UI decisions

## Required Artifacts For Normal UI Work

Use these templates under `docs/ai/current/` when the task profile marks UI evidence as required:

- `templates/UI-UX-Brief.md`
- `templates/Design-System.md`
- `templates/UI-Review.md`
- `templates/Visual-Evidence.md`

## Recommended Flow

1. Define product type, platform, stack, primary user goal, and high-risk surfaces.
2. Create `Task-Profile.json`.
3. Create `UI-UX-Brief.md` and update `Design-System.md` when UI direction matters.
4. Implement the smallest useful UI slice.
5. Capture visual evidence with route, state, viewport, and artifact path.
6. Add at least one non-screenshot evidence record: layout, accessibility, runtime, static frontend audit, or independent UI review.
7. Fill `UI-Review.md` and `Visual-Evidence.md` when applicable.
8. Run `python3 scripts/harness/gate.py all --tier normal --task-id <task-id>`.

## Pre-Delivery Checks

- Accessibility: contrast, focus, labels, keyboard, alt text.
- Interaction: hover/focus/active/disabled/loading/error states.
- Responsive: no horizontal scroll, mobile-first layout, readable line lengths.
- Typography/color: semantic tokens, consistent scale, no random raw hex drift.
- Motion: 150-300ms purposeful transitions, reduced-motion support.
- Performance: image dimensions, lazy loading, avoid layout shift.
- Evidence: screenshot-only completion is not enough for `normal+` UI work.
- Sensitive UI: use a redacted artifact or `no_screenshot_reason`.

## Long-Term State

If a project develops a durable visual system, move stable rules into:

```text
harness/design/design-system/MASTER.md
harness/design/design-system/pages/<page>.md
```

Page files should only contain deviations from `MASTER.md`.
