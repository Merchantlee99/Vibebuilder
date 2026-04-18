# Subagent-Manifest.md — <프로젝트명>

> **언제 이 파일을 만드는가** (선택적)
> - 메인 writer 외에 역할을 명시적으로 호출할 때
> - write scope 를 둘 이상으로 나눠야 할 때
> - reviewer, QA, security, release 중 누가 언제 개입하는지 문서화가 필요할 때
>
> 해당 없으면 이 파일 없이 진행해도 된다.

## 활성 역할

이 프로젝트에서 현재 활성인 역할과 각자의 경계.

### 메인 writer

- **Who**: <사람 이름 / AI 모델>
- **Write scope**: <경로 glob>
- **Invocation**: 기본 — 항상 활성

### <추가 역할 1>

- **Role id**: <planner | reviewer | validator | qa | security | release 중 택>
- **Who**: <사람 / AI>
- **Write scope**: <경로>
- **Read scope**: <경로>
- **Invocation**: <언제 호출되는가 — "Gate ① 시", "Plan 검토 시" 등>
- **종료 기준**: <이 역할의 임무가 끝났다고 판단하는 조건>

### <추가 역할 2>

...

## 역할 간 경계 (Boundary)

| 경계 | 규칙 |
|------|------|
| <role A> ↔ <role B> | <어떤 파일은 누가 소유. 언제 교차 검증> |

## 에스컬레이션 (Escalation)

| 상황 | 누구에게 에스컬레이션 | 방식 |
|------|---------------------|------|
| Retry 3회 초과 | <role> | Gate ③ learning 기록 + RCA 요청 |
| Scope drift 발견 | planner | Gate ⑥ 블록 → Plan.md 갱신 |
| Security 민감 변경 | security reviewer | Gate ② 필수 |
| Release 준비 | release engineer | `ship` 게이트 |

## 금지 조합

이 프로젝트에서 **절대 같이 돌리지 않는** 역할 조합.

- <예: reviewer 가 직접 production code 수정 — 예외 시 write scope 재선언>
- <예: 같은 AI 가 같은 slice 의 write 와 review 를 모두 담당 — Gate ② P2-F 가 차단>

---

**작성 가이드**:
- 이 파일은 **런타임 manifest.json + review-matrix.json** 과 일관되어야 한다
- 변경 시 `.claude/agents/manifest.json` 도 같이 업데이트하는 것이 보통
- 불필요한 역할을 미리 만들지 않는다. 필요한 순간에만 켠다.
