# ETHOS

## Why This Harness Exists

Codex app은 이미 강한 실행 능력을 가진다. 문제는 능력이 아니라 운영 방식이다. 장기 프로젝트에서 무너지는 지점은 보통 아래 셋이다.

1. 계획보다 구현이 앞서면서 scope가 번진다.
2. 병렬 작업이 늘수록 누가 무엇을 소유하는지 흐려진다.
3. 시간이 지나면서 이전 결정과 현재 코드가 어긋난다.

이 하네스는 그 세 지점을 잡기 위해 존재한다.

## Core Beliefs

### 1. Chat is transient, files are durable

대형 프로젝트의 기억은 채팅만으로 유지되지 않는다. 최소한 `Prompt.md`, `PRD.md`, `Plan.md`, `Implement.md`, `Documentation.md`, `Subagent-Manifest.md`에 고정되어야 한다.

### 2. Isolation beats caution

"조심해서 작업하자"보다 `worktree` 분리와 명시적 write scope가 더 강하다. 안전은 태도가 아니라 구조에서 나온다.

### 3. Parallelism needs ownership

Subagent를 많이 쓰는 것보다 잘 나누는 것이 중요하다. 병렬화는 경로 소유권, 종료 조건, merge 책임이 분명할 때만 가치가 있다.

### 4. Review is a different job from authoring

작성과 검토를 같은 흐름으로 섞으면 blind spot이 커진다. 리뷰는 구현 요약이 아니라 regression hunting이어야 한다.

### 5. Time is a first-class dimension

하루를 넘기는 작업은 기억이 흐려진다. 그래서 automation, telemetry, audit이 필요하다. 장기 지속성은 기능이 아니라 운영 레이어다.

### 6. Learning must change the next action

실패를 로그에만 남기면 죽은 지식이다. 반복되는 block, review failure, ownership conflict는 다음 작업 전에 prefetch되어야 하고, 충분히 반복되면 skill 제안으로 승격되어야 한다.

## What This Harness Optimizes For

- Codex app 단독 사용성
- 장기 대형 프로젝트의 안정성
- bounded parallelism
- reviewable process
- restart cost 감소

## What It Intentionally Rejects

- 훅 의존도가 높은 폐쇄적 통제
- 의미 없는 agent 남발
- write scope가 겹치는 병렬 구현
- 근거 없는 "완료" 선언
- 로그는 많은데 다음 행동에 반영되지 않는 운영

## Long-Run Success Criteria

- 새로운 세션이 들어와도 `Documentation.md`와 `.codex/context/`만 읽으면 즉시 재개할 수 있다.
- normal 이상 작업에서 누가 무엇을 수정했는지 `Subagent-Manifest.md`로 재구성 가능하다.
- 한 달 뒤에도 `events.jsonl`과 `learnings.jsonl`에서 반복 문제를 찾을 수 있다.
- 주간 retro나 audit가 실제로 다음 작업 방식에 반영된다.

## One-Line Summary

`Codex를 잘 쓰는 프레임워크`가 아니라 `Codex의 실행력과 Codex app 기능을 오래 버티게 만드는 운영체계`를 목표로 한다.
