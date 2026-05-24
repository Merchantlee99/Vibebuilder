# UI Evidence Review

## Use When

Use for frontend, product UI, non-web UI, accessibility, layout density, copy, interaction state, or visual quality changes.

## Stack

- PM: define user job, primary decision, anxiety, CTA, and success criteria.
- UI/UX skill: inspect information hierarchy, density, terminology, and state coverage.
- Visual reviewer: capture screenshots when safe and pair them with DOM/layout/accessibility evidence.
- Implementation evidence: map UI change to executed checks.
- Reviewer: compare customer UX, edge states, and residual risk.

## Required Gates

`intent_router_gate`, `design_gate`, `ui_evidence_gate`, and optionally `non_web_ui_evidence_gate`, `runtime_evidence_gate`, `accessibility` evidence, or `strict_gate` for sensitive screens.

## Stop Condition

Do not claim UX improvement from screenshots alone. Normal+ UI work needs screenshot plus layout, accessibility, runtime, or reviewer evidence.
