---
name: vibe-coding-workflow
description: Use once plan is locked and implementation needs to start. Guides a disciplined build loop with scope freeze, milestone-sized slices, validation after each slice, and document sync. Replaces the "start coding and see what happens" failure mode with a controlled march through the plan.
---

# Vibe Coding Workflow

Plan 이 잠긴 뒤 **구현 단계를 흐트러지지 않게 진행** 하는 skill.

## 언제 쓰는가

- `runtime.json → gates.scope_locked == true AND gates.plan_reviewed == true`
- `Prompt.md` / `PRD.md` / `Plan.md` 가 준비됨
- 중간 규모 이상 기능 (normal 또는 high-risk tier)
- scope 를 지키면서 milestone 단위로 전진해야 할 때

## 언제 쓰지 않는가

- 기획 단계 (→ `/office-hours`, `/product-planner`, `/plan-eng-review`)
- trivial tier (한 줄 수정)
- Plan 이 흔들리는 중 → 먼저 plan 잠금

## 핵심 방지 대상

구현 중 자주 터지는 세 가지 실패 모드를 구조적으로 막는다:

1. **Scope creep** — "이거 고치다 보니 저기도 손 보고 싶다"
2. **Implicit parallelism** — 한 번에 여러 branch 를 마음속으로 돌리다 혼동 (솔로도 발생)
3. **Doc drift** — 구현 끝났는데 Documentation.md 는 2 milestone 전 상태

## 워크플로

### 0. Pre-flight (시작 전 체크)

```
- runtime.json → gates.scope_locked: true
- runtime.json → gates.plan_reviewed: true
- Plan.md 의 milestone + slice 순서 확정
- Implement.md 빈 템플릿 준비
```

하나라도 안 되면 이 skill 대신 `/plan-eng-review` 로 돌아간다.

### 1. Milestone 하나 선택

- Plan.md 에서 가장 처음 slice 하나만 잡는다
- "전체 milestone" 을 한 번에 구현하려 하지 않는다
- Implement.md 의 "현재 작업 범위" 에 **이 slice 하나만** 적는다

### 2. Slice 단위 검증 루프

각 slice 는 다음 사이클:

```
write → test → validate → commit → update doc
```

- **write**: Plan 의 In-scope 파일만 touch. 다른 파일 생각나면 → Implement.md 의 "발견 사항" 에 적고 **멈추지 말되 수정하지 않음**
- **test**: Gate ④ (deterministic tool) 가 background 로 돌지만, 추가로 본인 시나리오도 확인
- **validate**: Plan 의 milestone 종료 조건 체크
- **commit**: 하나의 logical change = 하나의 commit
- **update doc**: Implement.md 에 "slice N 완료" + Documentation.md 에 "결정 로그 / 재개 지점"

### 3. Scope drift 발생 시

구현 중 "이거 고치다 보니 다른 파일도..." 가 떠오르면:

- **즉시 멈춘다**
- Implement.md 의 "발견 사항" 섹션에 적는다:
  - "발견: X 를 Y 해야 한다는 것을 구현 중 깨달았음"
  - "현재 slice 에서 처리? → no (Plan 에 없음)"
  - "다음 slice? / 별도 milestone? → 결정 대기"
- 이 발견이 중요하면: `/plan-eng-review` 로 돌아가서 Plan 갱신
- 사소한 관찰이면: Documentation.md 의 "Known Issues" 에 기록하고 현재 slice 계속

### 4. Milestone 완료

- Plan 의 해당 milestone 종료 조건 모두 체크
- `runtime_gate.py verify-implementation` 으로 `implementation_verified=true` 전환
- 다음 milestone → step 1 로

## 판단 기준 (구현 중)

| 상황 | 행동 |
|------|------|
| Plan 에 있는 범위 안의 버그 발견 | 현재 slice 에 포함, 고침 |
| Plan 에 없는 영향도 발견 | Implement.md 발견 사항 기록, 현재 slice 완료 후 plan 재검토 |
| 테스트가 애매하게 통과 | Gate ④ runner 로그 확인. "어떤 assertion 이 진짜 이 변경을 증명하나?" |
| "이거 refactor 하고 싶다" 유혹 | Plan 에 없으면 금지. Documentation.md 에 "refactor candidate" 기록하고 넘어감 |
| 두 milestone 을 합치면 편할 것 같다 | 병합 금지. 각 milestone 의 독립 검증 가능성이 중요 |

## 출력 형식

매 slice 완료 시 Implement.md 업데이트:

```
## Slice N — <날짜>
### Write paths
- <파일>
### Test / validation
- <실행한 명령 + 결과>
### 커밋
- <SHA> <type>(<scope>): <요약>
### 발견 사항 (현재 slice 밖)
- <있으면 기록, 없으면 "none">
### 다음 slice
- <다음 slice 이름 or "milestone 완료 → 다음 milestone">
```

## 가드레일

- Scope 밖 편집 = 즉시 멈춤 + 기록. 절대 "이번만" 넘어가지 않는다
- 구현 끝났는데 Implement.md / Documentation.md 업데이트 안 됐으면 **완료로 보지 않는다**
- 검증 없이 다음 slice 로 넘어가지 않는다
- 여러 milestone 을 한 번에 구현하지 않는다 (솔로도 마찬가지)
- Gate ② review 를 "마지막 장식" 으로 취급하지 않는다 — milestone 중간에도 필요하면 review

## 먼저 읽을 것

- `Prompt.md`, `PRD.md`, `Plan.md`
- `templates/Implement.md` — 양식
- `CLAUDE.md` 의 라우팅 정책 (tier × complexity)
- 선행 skill 결과: `product-planner` / `plan-eng-review` 의 verdict
