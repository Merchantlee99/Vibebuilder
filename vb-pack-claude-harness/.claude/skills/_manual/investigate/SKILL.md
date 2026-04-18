---
name: investigate
description: Use when something broke — a bug surfaced, a test regressed, a deploy misbehaved, or a user reported weird behavior. Enforces root-cause investigation BEFORE any fix. Separates proximate cause (what broke) from root cause (why it was possible) from systemic cause (why this class of bug exists in this codebase).
---

# Investigate

문제가 발생했을 때 **원인 파악 전 fix 를 시도하지 않게** 막는 skill.

## 언제 쓰는가

- 버그 / 회귀 / 이상 동작 관찰됨
- 같은 실패가 2회 이상 반복됨 (`learnings.jsonl` 에 `secondary-stuck-retry-2x` 류 패턴)
- 배포 후 이상 신호 (에러 로그 / 지표 이상)
- "왜 이게 이렇게 동작하지?" 가 머리에 맴도는 모든 순간

## 언제 쓰지 않는가

- 원인이 **이미 명백** 한 trivial 수정 (오타, 변수명 실수)
- 아직 증상 재현도 못 함 (그러면 먼저 재현 단계 필요)

## 핵심 규율

**원인 파악 전에 fix 를 시도하지 않는다.**

"일단 고치고 보자" = 반복 발생 위험 + 실제 원인 은폐. Gate ③
learning 기록은 **원인까지 분해된 후** 에 의미가 있다.

## 단계

### 1. 재현 (Reproduction)

- 증상을 한 번에 재현하는 **최소 단계** 기록:
  ```
  입력: <구체적 입력>
  단계: <클릭/명령어/API call>
  기대: <정상이면 이래야 함>
  실제: <버그 증상>
  빈도: always / sometimes / once-so-far
  ```
- 재현 안 되면 → 재현 환경을 먼저 만든다. 이 skill 은 여기서 멈춤.

### 2. Timeline 재구성

"어디서 비롯됐나" 를 **기록 기반** 으로:

- `git log` / `git blame` — 언제 이 경로가 바뀌었나
- `.claude/events.jsonl` — 최근 gate blocks / reviews / scope 변경
- `.claude/learnings.jsonl` — 비슷한 패턴이 과거 있었나 (`load_by_pattern`)
- `.claude/reviews/` — 최근 이 파일에 대한 리뷰
- `.claude/test-runs/run-*.log` — Gate ④ 가 왜 이 변경을 안 잡았나

기대와 다른 지점을 **시간 순서** 로 나열.

### 3. 3단 원인 분리

```
Proximate cause (무엇이 broken?)
  - 정확히 어떤 코드 줄 / 상태 / 흐름이 잘못된 결과를 냈나
  - "null pointer" 수준 아님. 그 null 이 왜 거기 있었나까지 1단계

Root cause (왜 proximate 가 가능했나?)
  - 어떤 invariant 를 믿었는데 실제로는 지켜지지 않았나
  - 어떤 데이터 형식이 예상과 달랐나
  - 어떤 순서 가정이 틀렸나

Systemic cause (왜 이 클래스의 버그가 이 코드베이스에서 가능한가?)
  - 언어 / 아키텍처 / 테스트 방식이 이 버그를 허용한 구조적 이유
  - "여기만 문제" 가 아니라 "이런 패턴은 또 생길 수 있음"
```

원인이 한 줄로 안 쓰이면 → 아직 **덜 조사됨**.

### 4. Fix 경로 설계 (아직 구현 X)

- **즉시 fix (Proximate)**: 지금 증상 멈추기
- **구조 fix (Root)**: 이 invariant 를 어떻게 강제하나
- **탐지 fix (Systemic)**: 같은 클래스 버그를 **다음에** 잡을 signal

구현은 이 skill 이 끝난 **뒤** `/vibe-coding-workflow` 로.

### 5. Learning 기록

원인 파악 끝나면 **반드시** learnings.jsonl 에 기록:

```bash
python3 scripts/harness/learning_log.py append <gate> <pattern> \
  "<proximate: 한 문장>" "<fix: 한 문장>"
```

패턴이 FAILURE_TAXONOMY 에 없는 신규면 → `taxonomy-proposals.md` 에 자동 기록 (`taxonomy_learner.py` 주기 실행).

## 출력 형식

```
# Investigation — <YYYY-MM-DD> — <slug>

## Reproduction
- 입력:
- 단계:
- 기대:
- 실제:
- 빈도:

## Timeline
- T0 <ts>: <first symptom or relevant change>
- T1 <ts>: <next>
- T2 <ts>: <discovery>

## Proximate cause
<1-2 문장>

## Root cause
<1-2 문장>

## Systemic cause
<1-2 문장. 이 클래스의 버그가 이 코드베이스에서 가능한 구조적 이유>

## Did existing learnings.jsonl predict this?
- <ts> — <관련 entry or "no prior warning">

## Fix plan (not yet implemented)

### Immediate (proximate)
- <concrete change>

### Structural (root)
- <invariant to enforce, new test to add, data validation to insert>

### Detection (systemic)
- <what signal would catch this class earlier>

## Learning recorded
- pattern: <FAILURE_TAXONOMY slug or proposed new>
- mistake: <1 sentence>
- fix: <1 sentence>
```

저장: `.claude/audits/investigation-<ts>-<slug>.md`

## 가드레일

- **Fix 먼저, 조사 나중 금지** — fix 는 이 skill 완료 후 별도 단계
- Proximate 만 적고 끝내지 않는다 — Root / Systemic 까지 쓰기
- "원인 모르겠음" 은 verdict 가 될 수 있다 — 그 경우 **추가 관찰 계획** 을 Fix plan 대신 적는다
- 이 investigation 결과는 `/vibe-coding-workflow` 의 새 plan 기반이 된다 (큰 수정이면)

## 먼저 읽을 것

- `.claude/events.jsonl` 최근 entries
- `.claude/learnings.jsonl` (비슷한 pattern 검색: `learning_log.py by-pattern <slug>`)
- `git log --since="2 weeks ago" -- <path>` — 최근 변경 이력
- `.claude/sealed-prompts/failure-analysis.md` — sealed prompt 구조 기준
