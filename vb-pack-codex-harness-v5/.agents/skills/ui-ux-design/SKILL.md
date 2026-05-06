---
name: ui-ux-design
description: Use when a task changes UI structure, visual design, interaction states, accessibility, responsive behavior, design systems, landing pages, dashboards, mobile screens, forms, charts, or frontend polish.
---

# UI/UX Design Intelligence

Use this skill whenever the work changes how a product looks, feels, moves, or is interacted with.

## Trigger

Use for:

- landing pages, dashboards, admin panels, SaaS screens, portfolio, blog, e-commerce, mobile app UI
- components: buttons, forms, modals, navbars, sidebars, cards, tables, charts
- styling: color, typography, spacing, layout, animation, dark mode, responsive behavior
- UX review, visual polish, accessibility checks, design-system creation

Skip for pure backend, API, database, infra, or non-visual automation work.

## Design Workflow

1. Identify product type, user goal, platform, stack, and primary action.
2. Create or update a design system before implementing visuals.
3. Define semantic tokens: color, typography, spacing, radius, elevation, motion.
4. Choose a visual direction intentionally. Avoid generic AI defaults.
5. Design mobile-first, then scale to desktop.
6. Validate accessibility, interaction states, forms, responsive layout, and performance.
7. Run a pre-delivery UI/UX anti-pattern check.

## Priority Checks

1. Accessibility: contrast, labels, keyboard navigation, focus states, alt text.
2. Touch and interaction: 44px+ targets, loading feedback, hover-independent actions.
3. Layout and responsive: no horizontal scroll, safe spacing, readable line lengths.
4. Typography and color: semantic tokens, 16px base body, consistent type scale.
5. Forms and feedback: visible labels, inline errors, recovery path.
6. Motion: 150-300ms meaningful transitions, reduced-motion support.
7. Performance: image dimensions, lazy loading, avoid layout shift.
8. Visual quality: coherent style, one icon language, one primary CTA per screen.

## Required Artifacts For Normal+ UI Work

- `docs/ai/current/UI-UX-Brief.md`
- `docs/ai/current/Design-System.md`
- `docs/ai/current/UI-Review.md`

Templates are available under `templates/`.

## Output Contract

Return:

- product and user goal
- design direction
- design tokens
- page/component structure
- accessibility and responsive checks
- implementation notes
- UX risks or follow-ups
