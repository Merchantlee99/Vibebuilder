# Subagent-Manifest.md — Codex Native Harness

## Roles

### Orchestrator

- Who: main Codex session
- Goal: scaffold and integrate the harness
- Mode: local
- Write scope: planning docs and final integration across the repo

### Explorer

- Who: none in v0 bootstrap
- Goal: reserved for future codebase questions
- Read scope: repository-wide
- Write scope: none
- Stop condition: answer a bounded question with file references

### Worker

- Who: none in v0 bootstrap
- Goal: reserved for disjoint implementation slices in future iterations
- Mode: worktree
- Write scope: assigned-only
- Read scope: assigned context plus shared docs
- Stop condition: complete bounded slice and report changed paths

### Reviewer

- Who: main session or future reviewer subagent
- Goal: verify structure, risk, and validation coverage
- Write scope: `.codex/reviews/**`
- Stop condition: produce a review summary with validation notes

## Boundaries

- Root governance docs are owned by the orchestrator.
- Future worker subagents must not overlap write scope.
- Reviewer should not patch the same production scope by default.
- Detailed per-agent dispatch specs should be generated with `python3 scripts/harness/subagent_planner.py plan ...` and persisted in `.codex/context/subagent-tasks.json`.

## Escalation

- If blocked 3 times on the same slice: update `Plan.md` before continuing.
- If scope drifts: revise `Plan.md` and `Documentation.md` first.
