# Spec Governance

This harness uses a compact intent-spec discipline for behavior that must stay
stable across long-running AI-assisted development.

## Rule

```text
docs explain; specs govern; evidence proves.
```

Narrative docs can explain background, rationale, or history. Governing
behavior belongs in `spec/` or the active `templates/Spec-Layer.md` artifact
until the project has a dedicated spec tree.

## Minimum Layers

| Layer | Use when |
| --- | --- |
| L0 constitution | product-wide values, authorities, forbidden shortcuts |
| L1 domain truth | shared nouns, states, IDs, ownership, scope, invariants |
| L2 behavior spec | any behavior change |
| L3 interface contract | async, external AI, ingestion, auth, deletion, privacy, retry, rollback, idempotency, partial failure, external integrations |

## Completion Boundary

Implementation is not complete because a requirement exists, a generated stub
exists, or a code path references `@Spec(...)`. Completion needs executed or
recorded evidence: test, guardrail, smoke, runtime proof, or named manual
review.

If code falls behind an accepted spec, keep the spec and classify the gap:

- `missing_implementation`
- `partial_implementation`
- `missing_test`
- `wrong_code`
- `wrong_spec`
- `decision_gap`

Only weaken a spec when the spec itself is unauthoritative, stale, out of
scope, or contradicted by stronger product, platform, security, privacy, or
ownership authority.
