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
- `artifact_class`: requested artifact class (`cli`, `web_app`, `web_service`, `data_pipeline`, `ui_surface`, `document`, `research_report`, `skill_harness`, `game`, or `unspecified`).
- `completion_mode`: intended finish state (`product_complete`, `code_complete`, `release_gate`, `supporting_or_read_only`, or `analysis_complete`).

## Artifact Evidence

Route is not enough. Evidence must match the artifact:

| Artifact | Minimum evidence |
| --- | --- |
| CLI/tool | command invocation, exit code, and representative output |
| Web app/UI | rendered visual proof for relevant viewport/state |
| Web service/API | request/response smoke or contract check |
| Data pipeline | fixture input/output diff or deterministic rerun |
| Skill harness | train and heldout route validation |
| Document/report | source consistency, citations when needed, and scope boundary |

Before final wording, run the safe-but-wrong check in
`references/ouroboros-lite-gates.md`: if the result is only supporting material,
do not call it product complete.

## Acceptance Rule

Any route change must pass:

```bash
python3 scripts/route_eval.py --suite train
python3 scripts/route_eval.py --suite heldout
```

Do not accept a change that fixes one prompt by regressing read-only, debug, review, release, design, or current-docs behavior.
