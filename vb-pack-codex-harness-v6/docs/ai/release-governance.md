# Release Governance

The harness should leave normal+ work commit-ready and release-affecting work
release-reviewable. It does not assume Codex may publish external state changes
without permission.

## Every Normal+ Task

- Inspect `git status --short --branch` before final reporting.
- Know which files changed and whether any user changes are unrelated.
- Keep the work as one logical commit candidate.
- Record validation evidence and residual risk.
- Do not commit, push, tag, publish a release, or open a PR unless requested or
  project policy allows it.

## Release-Affecting Tasks

Use `templates/GitHub-Release.md` when a change touches:

- version metadata
- public behavior
- package/install surface
- CLI/API contract
- migration or compatibility behavior
- deployment/release pipeline
- changelog, release notes, README, or public docs

## Release Candidate Gate

A candidate is reviewable only when these are known:

- source of truth for version
- changelog or release-note entry
- governing requirement IDs or explicit no-spec-change rationale
- validation commands and results
- independent review outcome
- rollback path
- release blocker test for open findings

## Publication Order

1. Update version metadata.
2. Update changelog or release notes.
3. Run required checks.
4. Commit the reviewed change.
5. Push the branch and update the PR.
6. Create tag `v<version>` from the reviewed commit.
7. Publish the GitHub release from that tag.
8. Record post-release smoke or artifact verification.

If checks fail, do not tag. If the tag exists but release publication fails,
retry publication from the existing tag instead of moving the tag.

## Blocker Rule

Do not call a finding a release blocker unless all are true:

```text
authoritative requirement
+ current target release
+ missing or partial implementation evidence
+ core journey impact
= blocker
```

If any condition is unknown, the release impact is `unknown`, not `blocker`.
