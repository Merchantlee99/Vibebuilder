# Ouroboros-Lite Gates

Use this reference when a route could otherwise finish with a generic "tests
passed" claim while solving the wrong artifact problem.

## Artifact Class

Before substantial work, name the requested artifact class:

| Artifact class | Done evidence |
| --- | --- |
| `cli` | headless command run, exit status, and representative stdout/stderr or golden output |
| `web_app` | local run or build plus rendered browser proof for the important viewport/state |
| `web_service` | API smoke or contract check with status/body evidence |
| `data_pipeline` | fixture input/output diff or deterministic rerun evidence |
| `ui_surface` | rendered visual proof, state coverage, and responsive check |
| `document` | source consistency check and scope confirmation |
| `research_report` | current/source-backed citations and fact-vs-inference split |
| `skill_harness` | train and held-out routing/evidence validation |
| `game` | runtime, visual, or playability probe rather than build-only evidence |

If the artifact class is `unspecified`, infer conservatively from the user's
wording and say when the final artifact is only supporting material.

## Completion Mode

Carry one completion mode through the turn:

- `product_complete`: the requested runnable/user-facing product behavior exists
  and has artifact-class evidence.
- `code_complete`: code changed and passes the relevant focused gate, but no
  user-facing product runtime was requested or proven.
- `release_gate`: a go/no-go gate with pass/fail, rollback posture, and residual
  risks.
- `supporting_or_read_only`: analysis, docs, design notes, review, or read-only
  output that must not be called a completed product.
- `analysis_complete`: a non-mutating decision or design is complete, with source
  references and assumptions stated.

## Safe-But-Wrong Gate

Before finalizing, compare the produced artifact against the user's original
artifact request:

- Did the artifact class change, such as CLI to docs, app to handoff, or batch
  tool to one-off checklist?
- Did the verification prove the requested behavior, or only prove that a file
  exists?
- Are missing data or unverified paths labeled as missing, unchecked, partial, or
  blocked instead of OK?
- Did a prior user correction in the same thread rule out this artifact shape?

If the artifact class drifted without user authority, mark the result partial or
blocked. Do not call it complete.

## Claim Gate

Map final claims to evidence:

```text
claim=<what will be said>
artifact_class=<cli|web_app|web_service|data_pipeline|ui_surface|document|research_report|skill_harness|game|unspecified>
completion_mode=<product_complete|code_complete|release_gate|supporting_or_read_only|analysis_complete>
evidence=<commands, screenshots, citations, files, evals>
gap=<not run, unavailable, partial, or blocked>
```

This is a lightweight discipline, not an instruction to run Ouroboros or depend
on Ouroboros internals.
