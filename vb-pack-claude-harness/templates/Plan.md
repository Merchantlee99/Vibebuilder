# Plan.md — <프로젝트명>

## Milestone 구조

Milestone 은 사용자 가치로 나눈 **독립 배포 단위**. 각 milestone 은 독립
적으로 검증 가능해야 한다.

### M1: <milestone 이름>
- **목표**: <한 문장>
- **In-scope 파일**: <경로들>
- **Out-of-scope 파일** (이번엔 건드리지 않음): <경로들>
- **검증 방법**:
  - <test, API, CLI, browser 중 어떤 것으로 검증하는가>
- **종료 조건**: <M1 이 끝났다고 선언하는 상태>

### M2: ...

## 구현 순서 (Ordered Slices)

각 slice 는 **하나의 커밋 단위**. milestone 하위.

| # | Slice | 소속 M | 대상 파일 | 검증 |
|---|-------|--------|----------|------|
| 1 | <기술 slice> | M1 | <files> | <how to verify> |
| 2 | ... | M1 | ... | ... |

## Rollback 계획

각 milestone 이 실패했을 때 **어떻게 되돌릴 것인가**.

- M1 실패 시: <어떤 commit 으로 revert, 어떤 환경 변수 리셋, 등>
- M2 실패 시: ...

## Blast radius

이 변경이 영향을 미치는 범위.

- 직접 영향: <코드 경로 / 기능>
- 간접 영향: <다운스트림 소비자 / 다른 팀>
- Blast 테스트 방법: <통합 테스트 / 카나리 / 모니터링>

## Tier 분류

| 항목 | 값 |
|------|-----|
| tier | <trivial | normal | high-risk> |
| complexity | <simple | complex> |
| reason | <왜 이 tier 인지 1-2 문장> |

## 종료 조건 (Plan done-when)

모든 milestone 이 끝났는지 판단하는 기준.

- [ ] 모든 M 의 종료 조건 충족
- [ ] Implement.md 에 write path 기록 완료
- [ ] Documentation.md 에 결정 로그 업데이트 완료
- [ ] Gate ② (상호 리뷰) 완료
- [ ] Gate ④ (결정론적 도구) green
- [ ] `ship` 게이트 통과 (릴리스 대상 시)

## 다음 gate

<review-matrix.json 에 따라 현재 stage 가 어디이고 다음에 어떤 reviewer 가
필요한지>

---

**작성 가이드**:
- Plan 은 **구현 상세**. 사용자 관점은 PRD 로.
- In-scope / Out-of-scope 가 명확해야 Gate ⑥ scope drift 를 막을 수 있다
- Tier 분류는 `size_check.py` 가 확인하는 것과 **일관** 해야 한다
