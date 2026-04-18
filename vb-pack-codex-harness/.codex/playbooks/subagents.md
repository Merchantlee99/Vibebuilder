# Subagents Playbook

## Use Subagents When

- 코드베이스 질문이 명확하고 독립적일 때
- 구현 slice를 경로 기준으로 분리할 수 있을 때
- 메인 세션이 통합과 다음 결정을 계속 진행할 수 있을 때

## Do Not Use Subagents When

- 바로 다음 행동이 그 결과에 막혀 있을 때
- 질문이 너무 넓어서 조사 범위가 무한정 커질 때
- 같은 파일을 둘 이상의 worker가 만질 가능성이 있을 때

## Role Defaults

- `explorer`: read-only 질문 응답
- `worker`: 명시된 write scope 구현
- `reviewer`: read-only 검토와 `.codex/reviews/` 산출물 작성

## Required Inputs

- 목표 한 문장
- 소유 경로
- 종료 조건
- 금지 경로
- 검증 기대치

## Preferred Preflight

```bash
python3 scripts/harness/subagent_planner.py plan --role worker --owner worker-auth --goal "auth slice" --write-scope src/auth --write-scope tests/auth --claim
```

- planner가 `dispatch_status=ready` 여야 실제 worker를 띄우는 것이 기본값이다.
- `dispatch_prompt`를 그대로 subagent 시작 메시지의 베이스로 쓴다.
- conflict가 있으면 owner 또는 write scope를 먼저 재설계한다.

## Integration Rule

메인 세션은 subagent 결과를 받아 그대로 믿지 말고, 통합 전 최소한 diff와 검증 명령은 다시 확인한다.
