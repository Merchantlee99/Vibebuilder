---
name: product-planner
description: Use after /office-hours when the problem is defined but the plan and scope are not yet ready. Judges readiness through discovery, product, and engineering lenses. Returns a readiness verdict (ready / revise / park) + concrete gaps to close before implementation starts.
---

# Product Planner

문제 정의는 끝났는데 (office-hours 이후) 아직 PRD / Plan 이 불안한 단계를
잠그는 skill.

## 언제 쓰는가

- `/office-hours` 이후 "이 문제는 풀 가치가 있다" 가 결정됨
- `PRD.md` 초안이 있지만 acceptance criteria 가 모호
- `Plan.md` 쓰기 전, 또는 쓴 뒤 "이 정도면 scope_lock 해도 될까?" 판단 필요
- 범위가 쉽게 커질 수 있는 기능 (예: 인증, 결제, 데이터 모델)

## 언제 쓰지 않는가

- 문제 정의 자체가 흔들림 → 먼저 `/office-hours` 로 돌아가기
- trivial tier (단일 파일, 2-3 줄 수정)
- 이미 `runtime.json → gates.plan_reviewed == true`

## 방식 (솔로 버전)

gstack/Manta 의 다면 렌즈를 **솔로 환경에 맞게 3개로 단순화**:

### 1. Discovery lens — "사용자 문제가 정말 이거 맞나?"

- PRD 가 주장하는 사용자 시나리오가 **실제로 1명 이상에게 관찰** 됐는가?
- 사용자가 지금 **어떻게 우회** 하고 있나? (수동 / 다른 도구 / 포기)
- 당신이 "사용자" 라면, 이 기능 대신 **다른 것** 을 만들어달라고 했을 가능성은?

### 2. Product lens — "이게 10x 인가, 1.1x 인가?"

- Acceptance criteria 가 **측정 가능** 한 숫자/상태로 적혀 있나?
- "OK" / "대충 좋음" 같은 애매 기준이 있으면 reject
- 이 기능이 사용자 워크플로에서 **몇 단계를 줄이거나 새로 가능하게** 하나?
- 1.1x 수준이면 → **park** verdict (지금 안 해도 됨)

### 3. Engineering lens — "지금 상태로 구현 시작하면 뭐가 터지나?"

- In-scope / Out-of-scope 파일이 **Plan.md 에 명시** 됐나?
- Milestone 이 **독립 검증 가능** 한 단위로 쪼개졌나?
- Rollback 계획이 있나 (한 milestone 실패 시 되돌릴 방법)?
- Tier 분류 (`size_check.py` 기준) 와 Plan 의 self-assessment 가 일치하나?
- high-risk 경로 (auth/security/payment/migration) 포함되면 명시?

## 출력 형식

```
# Product Planner Verdict — <date>

## Readiness: ready | revise | park

## Discovery lens
- 사용자 관찰 증거: <구체>
- 현재 우회법: <구체>
- Gaps: <있으면 list, 없으면 "none">

## Product lens
- 10x claim: <왜 10x 인지 또는 "1.1x, park 권장">
- Acceptance criteria 구체성: high / medium / low
- Gaps: <list>

## Engineering lens
- In/Out scope 명시: yes / no
- Milestone 쪼개기: good / weak
- Rollback 계획: yes / no / n/a
- Tier 정확성: <match / mismatch>
- Gaps: <list>

## Close-before-scope-lock list

구현 시작 전에 반드시 해결할 것:
1. ...
2. ...

## Next gate
- If ready → `runtime_gate.py lock-scope` + `runtime_gate.py review-plan`
- If revise → 위 close list 를 PRD.md / Plan.md 에 반영 후 재평가
- If park → Documentation.md 에 "parked: <reason>" 기록 후 다른 작업으로
```

## 가드레일

- "충분해 보인다" 금지 — lens 3개 모두 구체 근거 또는 gap 명시
- park verdict 는 포기가 아니라 "지금 아님" — Documentation.md 에 이유 기록
- 솔로 환경에서는 이 skill 이 `/office-hours` 와 `/plan-eng-review` 사이의 자연스러운 연결고리

## 먼저 읽을 것

- `Prompt.md`, `PRD.md`, (있으면) `Plan.md` 초안
- `ETHOS.md` — 무너지지 않는 철학
- `CLAUDE.md` — 운영 헌법
- `templates/PRD.md`, `templates/Plan.md` — 양식 기준
