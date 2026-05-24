---
name: intent-routing
description: Use first for normal or high-risk natural-language work to choose task mode, tier, grill path, spec layers, team-rule scan, and required gates before implementation.
---

# Intent Routing

Use this skill before meaningful edits when the user gives a natural-language request.

## Steps

1. Classify the request into a mode: exploration, spec authoring, implementation, reverse spec review, evidence mapping, release audit, team-rule mining, or repository maintenance.
2. Choose `trivial`, `normal`, or `high-risk`.
3. Decide whether to use `grill-me`, `grill-with-docs`, domain language, L1/L2/L3 spec, UI/runtime evidence, strict review, or team-rule mining.
4. Write `docs/ai/current/Intent-Routing.json`.
5. Run `scripts/harness/intent_router_gate.py`.

## Output Contract

Return the route, required gates, and why the route was selected. Do not silently skip the routing artifact for normal+ work.
