# Routing Contract

`classify_task.py` returns a JSON object with these top-level fields:

| Field | Meaning |
| --- | --- |
| `route` | One of `quick`, `normal`, `deep`, `ultra`, `design`, `debug`, `review`, `release` |
| `confidence` | Heuristic confidence score from 0 to 1 |
| `matched` | Keywords that influenced the route |
| `constraints` | Cross-turn boundaries to preserve |
| `suggested_skills` | Skills to hand off to next |
| `evidence_required` | Proof expected before completion |
| `forbidden_actions` | Actions blocked unless the user explicitly changes scope |

## Constraint Meanings

- `read_only`: no edits, commits, staging, migrations, formatters, or writes.
- `current_docs_required`: use official or current primary sources before unstable claims.
- `product_ui`: use product/UI references and rendered visual proof when implementation is in scope.
- `release_gate`: include go/no-go, risk inventory, rollback posture, and gate results.
- `security_sensitive`: include security/safety review and avoid exposing secrets.
- `skill_harness`: validate skill or routing changes with train and heldout fixtures.

## Acceptance Rule

Any route change must pass:

```bash
python3 scripts/route_eval.py --suite train
python3 scripts/route_eval.py --suite heldout
```

Do not accept a change that fixes one prompt by regressing read-only, debug, review, release, design, or current-docs behavior.
