# Automations Playbook

## Prefer Heartbeats

같은 프로젝트 스레드에서 이어가야 하는 작업이면 heartbeat automation이 기본값이다.

## Good Automation Targets

- 주간 retro
- pending audit follow-up
- stale task reminder
- 외부 응답 대기 후 재개
- pending review follow-up
- proposed skill triage

## Preferred Scan

```bash
python3 scripts/harness/automation_planner.py scan
```

- 결과는 `.codex/context/automation-intents.json` 에 기록된다.
- suggestion이 생기면 그중 실제 continuity 가치가 있는 것만 Codex automation으로 승격한다.
- 기본 추천은 `Pending Review Follow-up`, `Harness Evolution Sweep`, `Proposed Skill Triage` 다.

## Prompt Shape

- durable task 설명
- skip 조건
- 기대 출력

스케줄 정보는 prompt가 아니라 automation 설정에 둔다.
