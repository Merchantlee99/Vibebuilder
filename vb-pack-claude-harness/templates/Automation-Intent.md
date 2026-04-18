# Automation-Intent

프로젝트가 하루 이상 걸리거나 반복 점검이 필요한 경우 이 파일을 채운다. 이 파일이 없으면 automation_planner 는 기본 히트만 제시한다.

## Active Intents

<!--
each intent block:

### <short-name>
- kind: heartbeat | scheduled
- destination: thread | side-chat
- trigger:        python3 scripts/harness/<scriptName>.py ...
- cadence_hint:   next-working-block | daily | weekly
- expected_output: <what the next run should produce>
- skip_condition:  <when this becomes stale / unnecessary>
- evidence:        <file path or events.jsonl query showing need>
-->

(none)

## Rules

- Heartbeats preferred over cron when continuity in this thread matters.
- Prompt describes the task, not the schedule (the scheduler owns cadence).
- Skip condition MUST be concrete (file exists, tests green, etc.) so the loop can terminate.
- Evidence MUST reference a file or log query, not vibes.

## Triage Log

<!--
short dated notes on why an intent was added / demoted / archived.
-->

(empty)
