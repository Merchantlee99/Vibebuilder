---
name: office-hours
description: Use at the START of a new product idea or feature. Reframes user's raw request into a real problem worth solving before any code is written. Inspired by YC Office Hours. Returns a focused problem statement + go/no-go.
---

# Office Hours

사용자 요청을 받자마자 코딩으로 들어가지 말고, 먼저 **진짜 해결할 가치가
있는 문제인지** 를 확인하는 skill.

## 언제 쓰는가

- 새 기능 / 새 제품 / 새 워크플로를 시작할 때
- 요청이 모호하거나 "~ 같은 거 만들어줘" 형태일 때
- 진짜 사용자 가치가 무엇인지 불투명할 때

## 언제 쓰지 않는가

- 명백한 버그 수정
- 이미 정의된 acceptance criteria 안의 작업
- trivial tier (≤ 20 LOC, 1 file) 변경

## 방식

"YC partner 가 10분 미팅에서 하는 질문" 을 순서대로 던진다.

### 1단계 — 사용자가 누구인가?

- 한 문장으로 쓴다: "이 기능은 <누구> 가 <언제> <어떤 상황에서> 쓰는 것."
- "모든 사람" 이면 다시 질문한다. 구체 페르소나가 안 나오면 범위가 너무 넓다.

### 2단계 — 그 사용자가 지금 겪는 진짜 불편은?

- 지금 **무엇을 대신** 하고 있는가 (수동 / 우회 / 포기)?
- 그 불편이 얼마나 자주 / 얼마나 아픈가?
- 해결 안 되면 사용자가 **잃는 것** 은 무엇?

### 3단계 — 왜 지금 해결해야 하나?

- 지금이 아니면 안 되는 이유?
- 6개월 뒤로 미루면 어떻게 되나?
- 다른 해결책은 왜 안 되는가?

### 4단계 — 10x 제품은?

- 지금 구상하는 MVP 가 10x 개선인지 1.1x 개선인지.
- 만약 1.1x 면: 사용자는 **옮겨탈 이유** 가 없다. 범위를 바꾸거나 포기해야.

### 5단계 — 최소 proof

- "사용자가 가치를 느꼈다" 라고 선언할 수 있는 **가장 작은** 증거?
- 그 증거를 얻는 데 필요한 시간?
- 증거가 negative 로 나오면 어떻게 재조준?

## 출력 형식

```
Problem statement (1 문장):
<refined problem>

Target user (1 문장):
<who, when, what situation>

Current workaround:
<what user does now>

10x claim:
<why this is 10x, not 1.1x>

Smallest proof needed:
<what evidence, how long to get>

Verdict:
- GO — proceed to /plan-eng-review
- REVISE — <what to clarify first>
- PARK — <why this is not worth doing now>
```

## 가드레일

- 질문을 **대신 답하지 않는다**. 사용자가 각 단계에 답하게 한다.
- 사용자 답이 모호하면 다시 묻는다. 가짜 확신을 만들지 않는다.
- PRD.md 는 이 skill 이 끝난 **뒤에** 작성한다. 먼저 problem 을 명확히 하고 나서.
- 이 skill 의 verdict 가 GO 면 다음으로 `/plan-eng-review` 또는 `/product-planner` 로.

## 먼저 읽을 것

- `ETHOS.md` — 무너지지 않는 프레임워크 철학
- `CLAUDE.md` — 운영 헌법
- `templates/Prompt.md`, `templates/PRD.md` — 산출물 양식
