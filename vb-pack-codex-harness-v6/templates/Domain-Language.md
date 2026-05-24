# Domain Language

## Scope

Describe the bounded context or feature area this shared language governs.

## Canonical Terms

| Term | Meaning | Source / Authority | Rejected aliases |
| --- | --- | --- | --- |
| Example Term | The accepted meaning used by product, code, tests, and UI. | Product decision | Old Term |

## Entities

| Entity | Identity | Ownership | Notes |
| --- | --- | --- | --- |
| example_entity | example_id | system | Canonical entity name. |

## States

| State | Meaning | Allowed transitions |
| --- | --- | --- |
| draft | User-editable state. | draft -> submitted |

## Invariants

- The same canonical term must be used in spec, code, tests, and user-facing copy unless a UI-specific label is explicitly documented.

## Open Questions

- None.
