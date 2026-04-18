# Subagent-Manifest.md — <project>

## Roles

### Orchestrator

- Who: main Codex session
- Scope: planning, routing, integration
- Mode: local

### Explorer

- Who: <agent or none>
- Goal: <question>
- Read scope: <paths>
- Write scope: none
- Stop condition: <condition>

### Worker

- Who: <agent or none>
- Goal: <slice>
- Mode: worktree
- Write scope: <paths>
- Read scope: <paths>
- Stop condition: <condition>

### Reviewer

- Who: <agent or human or none>
- Goal: <review focus>
- Write scope: `.codex/reviews/**`
- Stop condition: <condition>

## Boundaries

- <Path owner rule>
- <No-overlap rule>
- Generated dispatch specs may also live in `.codex/context/subagent-tasks.json`

## Escalation

- If blocked 3 times: <who decides>
- If scope drifts: <who updates Plan.md>
