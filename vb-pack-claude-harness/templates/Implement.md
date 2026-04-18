# Implement.md — <프로젝트명>

## 현재 작업 범위 (Current Scope)

**이번 slice 만** 여기 적는다. 끝나면 다음 slice 를 위해 업데이트.

- **Milestone**: <M1 | M2 | ...>
- **Slice**: <slice 이름>
- **write paths** (이 slice 에서 건드리는 파일):
  - <path/to/file.py>
  - <path/to/other.py>
- **read-only paths** (이 slice 에서 참고만 하는 파일):
  - <path>
- **금지 paths** (이 slice 에서 절대 건드리지 않는 파일):
  - <path>

## 검증 루프 (Validation Loop)

이 slice 가 끝났다고 선언하기 전에 돌릴 것:

```bash
# 1. 단위 테스트
<command>

# 2. 린트 / 타입 체크
<command>

# 3. 재현 또는 시연
<command>
```

기대 출력 (tail 10줄):
```
<expected output sample>
```

## 현재 상태

| 단계 | 상태 | 비고 |
|------|------|------|
| failing_tests_committed | ☐ | <아직 / 완료> |
| implementation_verified | ☐ | <아직 / 완료> |
| deterministic_verified | ☐ | <아직 / 완료> |

## 발견 사항 (Findings)

구현 중 발견한 것들 — PRD/Plan 에 반영해야 할 것들.

- <발견 1> → Plan.md 의 <어느 섹션> 업데이트 필요
- <발견 2> → 추가 slice 필요할지 검토

## 현재 블록커 (Blockers)

진행을 막고 있는 것.

- <blocker 설명>

## 다음 slice 로 넘어가기 전 체크리스트

- [ ] 위 검증 루프 전부 green
- [ ] Documentation.md 에 이번 slice 결정 기록
- [ ] 커밋 메시지에 slice 번호 포함 (예: `feat(M1-S2): ...`)
- [ ] Gate ② review-needed 가 events.jsonl 에 기록됨 (자동)
- [ ] 필요 시 reviewer invoke 후 `02 pass <actor>` 기록

---

**작성 가이드**:
- Implement.md 는 **현재 작업만**. 과거 slice 는 Documentation.md 로 이관
- write_paths 가 비어있으면 아직 slice 정의가 안 된 것
- 검증 루프가 비어있으면 "tests actually exercising this change" 를 증명할 수 없다
