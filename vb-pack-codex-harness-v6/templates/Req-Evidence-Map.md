# REQ Evidence Map

Task ID: task-v6-example

## Evidence Boundary

Generated stubs and trace comments are work slots, not completion evidence. A statement is complete only when the mapped test, guardrail, smoke check, runtime/UI review, or named manual review has executed or has an accepted block reason.

## Map

| Requirement / statement | Evidence state | Evidence type | Evidence target | Execution / record |
| --- | --- | --- | --- | --- |
| REQ-EXAMPLE-001:S1 | verified | unit | `tests/example.test.ts` | `python3 -m unittest discover -s tests -q` passed |
| REQ-EXAMPLE-002:S1 | manual_only | manual UX | `docs/ai/current/Review.md` | reviewer accepted manual recovery check |
