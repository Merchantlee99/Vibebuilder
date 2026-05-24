# Intent-Routed Implementation

## Use When

Use for normal+ coding work where the user gives a natural-language goal and expects implementation.

## Stack

- PM: clarify user goal, acceptance criteria, non-goals, and rollback.
- Router: create `docs/ai/current/Intent-Routing.json`.
- Spec: add `Domain-Language.md`, `Feature-Spec.md`, and `Req-Evidence-Map.md` when the route asks for language or spec authority.
- Implementer: keep changes scoped to routed files and accepted requirements.
- Reviewer: verify implementation evidence and unresolved risk.

## Required Gates

`intent_router_gate`, then route-selected gates, then implementation/review evidence through `gate.py all`.

## Stop Condition

Stop before code changes when route, scope, required spec layer, or high-risk tier is ambiguous.
