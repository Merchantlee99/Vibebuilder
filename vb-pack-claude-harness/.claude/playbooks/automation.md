# Automation Playbook

## Create automation when

- Task spans > 1 day
- Pending audit / review needs resume later
- Waiting state (external thing pending) longer than same-turn
- Weekly retro / hygiene loop is useful

## Avoid automation when

- Trivial one-shot task
- Same-turn follow-up is sufficient
- Cadence is one-off

## Claude Code tools

| Tool | When | Note |
|------|------|------|
| `ScheduleWakeup` | self-paced /loop continuation | in-session only |
| `loop` skill | recurring prompt on interval | `/loop 5m /foo` |
| `schedule` skill (`anthropic-skills:schedule`) | cron-style scheduled agents | cross-session |
| `scheduled-tasks` MCP | managed task list | full lifecycle |

## Integration with harness

1. Fill `Automation-Intent.md` with active intents (kind, trigger, cadence, skip_condition, evidence).
2. Run `python3 scripts/harness/automation_planner.py scan` — detects signals + proposes intents at `.claude/context/automation-intents.json`.
3. Use the recommended tool (ScheduleWakeup / schedule skill / loop) to actually arm the automation.
4. Weekly: `automation_planner.py list` to see active intents; archive stale ones.

## Detected signals (current version)

- `pending_review_followup` — review-needed with no matching pass
- `harness_evolution_sweep` — no insights-*.md in last 7 days
- `proposed_skill_triage` — anything in `.claude/skills/_evolving/`
- `learnings_taxonomy_review` — ≥5 new learnings since last taxonomy sweep

## Intent contract

Every automation intent MUST have:
- `name` — unique, snake_case
- `kind` — heartbeat | scheduled
- `destination` — thread | side-chat
- `cadence_hint` — next-working-block | daily | weekly
- `trigger` — exact command that runs
- `skip_condition` — CONCRETE check that terminates the loop
- `expected_output` — what a successful run produces
- `evidence` — file path or events.jsonl query showing the intent is still needed

Missing `skip_condition` → infinite loop. Missing `evidence` → automation nobody needed.

## Cleanup

- `automation_planner.py scan` re-evaluates all signals — intents that no longer fire are dropped from `intents.json`.
- Heartbeats that fulfilled their `skip_condition` should be explicitly stopped in Claude Code.
- Weekly review: run `automation_planner.py list` and prune.
