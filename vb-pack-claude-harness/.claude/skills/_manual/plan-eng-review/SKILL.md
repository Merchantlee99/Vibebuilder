---
name: plan-eng-review
description: Use after PRD is ready but before implementation. Locks architecture, data flow, edge cases, and test plan so scope cannot silently creep during build.
---

# Plan Engineering Review

구현 시작 전에 **architecture / data flow / edge cases / test plan** 을
잠그는 skill. Scope freeze 직전 단계.

## 언제 쓰는가

- PRD.md 가 작성돼 있고 Prompt.md 에 done-when 이 명시됨
- Plan.md 초안이 있지만 아직 가장자리 케이스를 검토 안 함
- tier 가 normal 또는 high-risk

## 언제 쓰지 않는가

- trivial tier 변경
- PRD 자체가 아직 흔들림 → 먼저 `/office-hours` 로 돌아가기

## 방식

Plan.md 를 **적대적으로 읽고** 다음을 잠근다.

### 1. Architecture 잠금

- 이 변경이 건드리는 **추상 경계** 는? (API / DB / queue / etc)
- 새로 추가되는 **추상** 은? (새 클래스 / 서비스 / 테이블)
- 그 추상이 **지금 꼭 필요한가** — 나중에 만들어도 되는가?

### 2. Data flow 잠금

- 입력 → 변환 → 저장 → 출력 경로를 **한 그림으로** 그린다.
- 각 경계에서 데이터 **형식과 책임** 을 기록.
- 실패 시 데이터는 어떻게 되나 (멈추나 / 롤백하나 / 일관성 깨지나)?

### 3. Edge cases 잠금

명시적으로 다음을 점검:

- 빈 입력 / 큰 입력 / 중복 요청
- 동시성 (lock order, race condition)
- 타임아웃 / 재시도 / 부분 실패
- 권한 없는 사용자 / tenant boundary
- 스키마 변경 시 기존 데이터 호환성
- 성능: O(n²) 경로 있나?

### 4. Test plan 잠금

- 각 AC (acceptance criterion) 에 **대응하는 테스트** 가 있나?
- 실패 경로를 테스트하는 fixture 가 있나?
- E2E vs 단위 vs 통합 구분이 명확한가?
- 기존 테스트를 **수정** 할 계획이 있나 → 그건 red flag

### 5. Tier 확정

- `size_check.py` 로 예상 tier / complexity 확인
- 예상과 다르면 Plan 을 쪼갠다

## 출력 형식

```
# Plan-Eng Review — <날짜>

## Architecture verdict
- Accept / Revise
- Issues found: <list>

## Data flow verdict
- Accept / Revise
- Missing boundaries: <list>

## Edge cases checklist
- [x] empty input
- [x] large input
- [x] concurrency
- [ ] <항목> — NOT covered in plan

## Test plan verdict
- Accept / Revise
- AC → test mapping: <table>
- Risky test modifications: <list>

## Tier confirmation
- Classified: <tier> / <complexity>
- Plan says: <tier>
- Match: yes / no

## Blocking issues (must fix before scope_lock)
1. ...

## Non-blocking suggestions
1. ...

## Next gate
If Accept → `runtime_gate.py lock-scope` + `runtime_gate.py review-plan`
```

## 가드레일

- "looks good" 금지. 최소 3개 objection 또는 `<INSUFFICIENT_OBJECTIONS>`.
- Plan 에 없는 edge case 를 찾으면 **plan 에 추가** 하고 다시 검토.
- 이 skill 완료 후에만 `lock-scope` / `review-plan` gate flag 를 flip.
- Layer 2 review-matrix 에서 `planner` 의 required_reviewers 역할을 수행.

## 먼저 읽을 것

- `Plan.md`
- `PRD.md`
- `CLAUDE.md`, `AGENTS.md`
- `.claude/sealed-prompts/plan-redteam.md`
