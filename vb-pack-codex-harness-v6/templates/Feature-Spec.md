---
id: SPEC-EXAMPLE
title: Example Feature Spec
status: active
owners: [main-codex]
layers: [L0, L1, L2]
---

# Example Feature Spec

## Scope

Describe the product or system behavior governed by this spec.

## Layer 0: Constitution

- The system must preserve user intent and report unverifiable behavior as a gap instead of silently weakening the accepted standard.

## Layer 1: Domain Truth

Canonical terms:

- `example_entity`: accepted domain entity.
- `example_state`: accepted state name.

Invariants:

- Canonical terms must stay consistent across spec, implementation, test names, and UI copy unless an explicit mapping exists.

## Layer 2: Behavior Spec

- [REQ-EXAMPLE-001:S1][Event-driven] When the user submits a valid example request, the system shall preserve the request and return a user-visible result.
- [REQ-EXAMPLE-002:S1][Unwanted] If processing fails after valid input is received, the system shall preserve the input and return a retry path, still-processing state, recoverable draft, or actionable error.

## Layer 3: Interface Contract

Required only when ordering, idempotency, retry, rollback, compensation, partial failure, payment, entitlement, deletion, or external integration matters.

Ordering:

1. Validate authority and input.
2. Persist the accepted request.
3. Execute the side effect.
4. Record completion or recoverable failure.

Idempotency:

- Repeating the same request key must not duplicate irreversible effects.

Partial failure:

- If downstream work fails after valid input is accepted, preserve the input and return a recoverable state.

## Verification Map

| Requirement / statement | Evidence |
| --- | --- |
| REQ-EXAMPLE-001:S1 | mapped in `Req-Evidence-Map.md` |
| REQ-EXAMPLE-002:S1 | mapped in `Req-Evidence-Map.md` |
