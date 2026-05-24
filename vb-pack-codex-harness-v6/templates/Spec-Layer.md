# Spec Layer

Use this artifact when a task changes product behavior, shared vocabulary,
system state, permissions, persistence, async work, external integrations, or
release-critical contracts.

## Task Mode

- Mode: spec authoring / implementation / reverse review / evidence mapping / release audit / method update
- Completion rule:
- Current claim: complete / partial / blocked / unverified / manual_only

## L0: Constitution

Product-wide values, authorities, and forbidden shortcuts.

- Authority:
- Forbidden shortcuts:
- Safety/privacy/security constraints:

## L1: Domain Truth

Shared nouns, states, IDs, ownership, scope, and invariants.

| Term or state | Meaning | Owner / source of truth | Invariant |
| --- | --- | --- | --- |
|  |  |  |  |

## L2: Behavior Spec

Use stable requirement IDs. Split multi-statement requirements into statement
IDs during verification.

- [REQ-XXX-001][Ubiquitous] The system shall ...
- [REQ-XXX-002][Event-driven] When ..., the system shall ...
- [REQ-XXX-003][State-driven] While ..., the system shall ...
- [REQ-XXX-004][Unwanted] If ..., then the system shall ...
- [REQ-XXX-005][Optional] Where ..., the system shall ...

## Feature Archetype Review

| Archetype | Applies? | Edge cases to settle | Requirement or contract |
| --- | --- | --- | --- |
| Async customer operation | yes / no | timeout, pending, retry, refresh, re-entry | REQ-XXX-### / L3 |
| Source or file ingestion | yes / no | parse failure, input preservation, split/retry | REQ-XXX-### / L3 |
| External AI or automation | yes / no | schema failure, partial output, low confidence, valid input failure | REQ-XXX-### / L3 |
| Approval or decision | yes / no | duplicate submit, stale state, actor authority | REQ-XXX-### / L3 |
| Payment, entitlement, or billing | yes / no | idempotency, double charge, provider/local mismatch | REQ-XXX-### / L3 |
| Auth or account | yes / no | replay, state mismatch, partial session | REQ-XXX-### / L3 |
| Deletion or privacy | yes / no | authorization, retention, audit, idempotency | REQ-XXX-### / L3 |
| External integration | yes / no | provider timeout, retry, local persistence failure | REQ-XXX-### / L3 |

## L3: Interface Contract

Required for async, deletion, privacy, auth, retry, rollback, idempotency,
partial failure, cross-resource mutation, or external integrations.

- Caller:
- Callee:
- Request:
- Response:
- Auth / permission:
- Ordering:
- Idempotency:
- Partial failure:
- Rollback / compensation:
- Latency shape: synchronous / long request / polling / background job / streaming

## Valid Input Failure

If valid user input is accepted and automation fails, preserve the input and
return a recoverable draft, still-processing state, retry path, or actionable
error.

| Valid input | Failing automation | Preserved data | Recovery result | Requirement |
| --- | --- | --- | --- | --- |
|  |  |  |  | REQ-XXX-### |

## Verification Map

Generated stubs are obligations, not proof. A statement is verified only after
real test, guardrail, smoke, runtime, or named manual evidence has executed or
been recorded.

| Requirement / statement | Evidence type | Evidence target | Execution / record | Status |
| --- | --- | --- | --- | --- |
| REQ-XXX-001:S1 | unit / integration / API / UI / guardrail / smoke / manual |  |  | generated_stub / mapped / traced / verified / manual_only / blocked |

## Gap Ledger

Do not downgrade accepted specs to match incomplete code. Keep the standard and
classify the mismatch here.

| Gap | Classification | Evidence reviewed | Spec action | Code / evidence action |
| --- | --- | --- | --- | --- |
| GAP-XXX-001 | missing_implementation / partial_implementation / missing_test / wrong_code / wrong_spec / decision_gap |  | keep / modify / decide |  |

## Release Impact

Do not mark a finding as a blocker until all four checks are known.

| Requirement or gap | Authoritative? | Target release? | Evidence checked? | Core journey? | Impact |
| --- | --- | --- | --- | --- | --- |
| REQ-XXX-001 | yes / no / unknown | current / next / later / unknown | yes / no | yes / no | blocker / non_blocker / proposal_only / unknown |
