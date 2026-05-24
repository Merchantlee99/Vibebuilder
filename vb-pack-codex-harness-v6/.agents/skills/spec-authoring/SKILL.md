---
name: spec-authoring
description: Use when behavior changes need L1/L2/L3 intent specification, EARS requirements, feature archetype prompts, latency contracts, or rollback/idempotency decisions.
---

# Spec Authoring

Use this skill before implementing behavior changes that need accepted intent.

## Steps

1. Select required layers: L1 for shared language, L2 for behavior, L3 for rollback/idempotency/partial failure.
2. Write EARS requirements with stable `REQ-...:Sx` statement IDs.
3. Include at least one `[Unwanted]` behavior for meaningful customer-facing work.
4. Apply feature archetype prompts for async, ingestion, external AI, approval, payment, auth, deletion, and integration work.
5. Run `scripts/harness/spec_gate.py`.

## Output Contract

Return the spec path, selected layers, REQ IDs, unwanted behavior coverage, and open decision gaps.
