# Automation-Intent.md — Codex Native Harness

## Active Strategy

- Run `python3 scripts/harness/automation_planner.py scan` to generate current automation suggestions into `.codex/context/automation-intents.json`.
- Promote a suggestion into a real Codex heartbeat only when the task truly spans time or needs a scheduled follow-up.
- Keep automation prompts durable: task only, no schedule wording inside the prompt body.

## Default Loops

### Pending Review Follow-up

- kind: heartbeat
- destination: thread
- use when: latest review artifact is still pending or blocked
- expected output: updated review artifact or explicit blocker note

### Harness Evolution Sweep

- kind: heartbeat
- destination: thread
- use when: insights are stale, blocked events accumulated, or learnings should be promoted into skills
- expected output: fresh insights report and one concrete process adjustment

### Proposed Skill Triage

- kind: heartbeat
- destination: thread
- use when: `.codex/skills/_proposed/` is no longer empty
- expected output: promotion, revision, or archive decision per proposed skill

## Current State

- Template mode does not force any always-on automation.
- Copied project instances should create one or more heartbeats when real follow-up continuity is required.
