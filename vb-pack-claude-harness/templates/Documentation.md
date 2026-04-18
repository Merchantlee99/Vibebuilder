# Documentation.md — <프로젝트명>

## 상태 (Current State)

| 항목 | 값 |
|------|-----|
| Framework version | unified-4-axis-1.0 |
| Current milestone | <M1 / M2 / ...> |
| Current stage | <plan / tests / implementation / verification / postmortem / done> |
| Last updated | <YYYY-MM-DD> |
| Last session id | <session id> |

## 재개 지점 (Resume Point)

다음 세션이 시작될 때 **어디부터 이어갈지** 1-2 문장으로.

<다음 세션에서 가장 먼저 할 일>

## 결정 로그 (Decision Log)

시간순, 최신이 아래. 각 결정은 **왜** 를 포함.

### <YYYY-MM-DD> — <결정 주제>
- **결정**: <무엇을 정했나>
- **대안**: <고려했지만 채택 안 한 것들>
- **이유**: <왜 이 결정인가>
- **영향**: <어떤 파일 / 흐름이 바뀌었나>

### <YYYY-MM-DD> — ...

## Known Issues

현재 알려진 미해결 문제. 각 항목은 **우회 방법** 또는 **후속 액션**.

- **<issue>**: <설명>. 우회: <workaround>. 후속: <plan>.

## 테스트 & 재현 방법

### 단위 테스트
```bash
<command>
```

### 통합 / E2E
```bash
<command>
```

### 로컬 실행
```bash
<command>
```

### 데모 시나리오
1. <단계>
2. <단계>

## 다른 사람이 이어받을 때

이 프로젝트를 처음 보는 사람이 **30분 안에 작업 가능** 하게 하기 위한 팁.

- 먼저 읽을 파일: Prompt.md → PRD.md → Plan.md → (이 파일) → Implement.md
- 핵심 도메인: <무엇>
- 자주 쓰는 명령: <list>
- 주의 사항: <함정>

## 변경 이력 (Changelog)

중요 milestone 완료 시점만 기록. 커밋별 상세는 git log 가 담당.

- **<YYYY-MM-DD>**: <M1 완료 요약>
- **<YYYY-MM-DD>**: <M2 완료 요약>

---

**작성 가이드**:
- Documentation.md 는 **장기 메모리**. 채팅 세션이 끝나도 남아야 할 내용만.
- 결정 로그는 "왜" 가 핵심. "무엇" 은 git log 로 충분.
- Known Issues 는 **active 상태** 만. 해결된 건 Changelog 로 이동.
- 재개 지점은 다음 세션 열 때 가장 먼저 읽는 문장이다.
