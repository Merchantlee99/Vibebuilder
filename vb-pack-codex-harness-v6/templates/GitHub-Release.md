# GitHub Release Readiness

Use this for normal+ changes that should be commit-ready, and always for
version, packaging, installation, public API/CLI, migration, deployment, or
release-note changes.

## Scope

- Task:
- Branch:
- Base branch:
- Issue / PR:
- Release intent: none / candidate / publish
- Target version:
- Version bump: none / patch / minor / major / prerelease

## Git State

- `git status --short --branch`:
- Files changed:
- Staged files:
- Untracked files:
- Dirty worktree accepted? yes / no

## Spec And Requirement Trace

- Spec impact: none / L0 / L1 / L2 / L3
- Governing REQ or statement IDs:
- Verification obligation:

## Version Sources

| Surface | Source of truth | Expected value | Verified? |
| --- | --- | --- | --- |
| package / app version | package.json / pyproject.toml / Cargo.toml / app config / other |  | yes / no / n/a |
| changelog / release notes | CHANGELOG.md / release notes file |  | yes / no / n/a |
| public docs | README / docs / website |  | yes / no / n/a |
| migration or compatibility note | docs / runbook / release note |  | yes / no / n/a |

## Validation Evidence

| Check | Command or artifact | Result |
| --- | --- | --- |
| lint/typecheck/test/build |  | pass / fail / blocked |
| harness gates |  | pass / fail / blocked |
| smoke/runtime/manual review |  | pass / fail / blocked |
| independent review |  | accept / block / follow-up |

## Release Blocker Test

Only mark `blocker` when every column is yes.

| Finding | Authoritative requirement | Current target release | Missing/partial evidence | Core journey impact | Impact |
| --- | --- | --- | --- | --- | --- |
|  | yes / no / unknown | yes / no / unknown | yes / no / unknown | yes / no / unknown | blocker / non_blocker / proposal_only / unknown |

## Rollback

- Code rollback:
- Data or migration rollback:
- Release rollback:
- User-visible recovery:

## Allowed External Actions

Codex should not perform these unless the user requested them or project policy
explicitly allows them.

- Commit: allowed / not allowed
- Push: allowed / not allowed
- PR create/update: allowed / not allowed
- Tag: allowed / not allowed
- GitHub release publish: allowed / not allowed

## Publication Checklist

1. Version metadata updated.
2. Changelog or release notes updated.
3. Required checks passed or blockers recorded.
4. Review accepted.
5. Commit created with one logical change.
6. Branch pushed.
7. PR created or updated.
8. Tag `v<version>` created from the reviewed commit.
9. GitHub release published from the same tag.
10. Post-release smoke or artifact check recorded.

## Residual Risk

-
