# ETHOS — 장기 내구성 철학

**이 프레임워크가 무너지지 않는 이유와 무너질 수 있는 조건.**

## 왜 "무너지지 않는" 프레임워크가 필요한가

단일 AI + 단일 세션으로 코딩하면 발생하는 세 가지 문제:

1. **확증 편향** — 자기가 맞다고 생각한 걸 끝까지 맞다고 여김
2. **터널 비전** — 자기가 분석하는 것만 분석함
3. **장기 드리프트** — 긴 프로젝트에서 품질이 서서히 무너짐

이 중 **3번 장기 드리프트** 가 가장 무섭다. 1-2번은 세션 단위 리뷰로 잡을 수 있지만, 3번은 6개월에 걸쳐 조용히 누적된다:
- 규칙이 너무 많아지면 팀이 "이번만 생략" 을 습관화
- 문서와 실제 코드가 조금씩 어긋남
- 초기에 설정한 tier 임계값이 프로젝트 성장을 못 따라감
- sealed-prompt 가 새 AI 모델과 호환 안 됨
- 상태 파일이 무한 증가해 관리 불가

## 네 가지 내구성 축

장기적으로 무너지지 않으려면 **네 축 모두**에서 살아남아야 한다:

| 축 | 질문 | 이 프레임워크의 대응 |
|---|------|-------------------|
| **시간** | 6개월 뒤에도 유효한가? | Layer 4 self-evolving + framework version migration |
| **규모** | 1000 파일 / 5명 팀에서도 작동? | segmented append-only logs + per-session 분리 + tier auto-tuning |
| **진화** | 새 모델·도구·패턴에 적응? | taxonomy self-growth + skill auto-gen + sealed-prompt aging |
| **불변식** | 악용되지 않는가? | actor crossover + Gate ⑦ + 사용자 승인 필수 |

## 무너지지 않는 원칙 8개

### 1. AI 성실성에 의존하지 않는다
- 프롬프트로 "조심하세요" 하지 않는다
- 위반은 `exit 2` 로 기계 차단
- AI 가 지시를 어기더라도 하네스가 막는다

### 2. Append-only 감사 로그
- `events.jsonl` 과 `learnings.jsonl` 은 **절대 rewrite** 안 된다
- Rotate 는 segment rename 방식 (데이터 보존). live 파일을 marker 한 줄로 덮지 않는다
- 과거 결정의 맥락은 무기한 추적 가능

### 3. 상호 검증이 기계적으로 강제된다
- 같은 AI 가 자기 작업을 자기가 "리뷰 완료" 기록할 수 없다 (actor crossover)
- sealed-prompt 구조 지문이 없는 리뷰 파일은 Gate ② 를 통과 못 한다
- 코드 리뷰는 7가지 rollback 조건을 explicit 체크해야 한다

### 4. 자가진화는 제안만
- Layer 4 의 모든 학습 결과는 `.claude/audits/` 에 **제안** 으로 기록
- 적용은 사용자 명시 승인 경유
- 프레임워크가 자기 규칙을 혼자 느슨하게 못 한다

### 5. 학습이 행동에 자동 반영된다
- `memory_manager.py` 가 매 턴 pre-hook 에서 관련 learnings top-5 를 주입
- 같은 파일의 과거 실패를 다음 편집이 자동 참조
- 학습이 로그에만 쌓이고 행동에 안 반영되는 "죽은 지식" 방지

### 6. 필수 산출물이 세션 간 맥락을 고정한다
- `Prompt.md` / `PRD.md` / `Plan.md` / `Implement.md` / `Documentation.md` / `Subagent-Manifest.md`
- 채팅 세션이 끝나도 다음 세션이 이 파일들로 즉시 맥락 복구
- "AI 가 까먹었어" 문제가 구조적으로 사라짐

### 7. 복구 경로가 설계되어 있다
- `runtime.json` 스키마 버전 + migration scripts
- 훅 circuit breaker (3회 연속 실패 시 자동 disable + 알림)
- 프레임워크 버전 업그레이드 경로 내장

### 8. 장기 사용자 모델
- 프로젝트의 전형적 PR 크기, 팀 리뷰 스타일, 자주 쓰이는 패턴을 `memory/project-profile.md` 에 누적
- 6개월 후 프레임워크가 "이 프로젝트 스타일" 을 알고 있다

## 무너질 수 있는 조건 (정직한 한계)

다음 상황에서는 **어떤 프레임워크도** 지탱 못 한다:

### 1. 사용자가 의도적으로 disable
- `.claude/settings.local.json` 의 훅을 빈 배열로 만들면 Layer 3 기계 차단이 꺼진다
- Layer 4 Self-evolving 이 이 disable 을 감지해서 사용자에게 경고는 할 수 있지만, 적용 강제는 불가
- **프레임워크는 사용자 의지를 넘지 않는다**

### 2. 프로젝트 철학의 근본 전환
- monorepo → microservices
- TypeScript → Rust
- solo → 20-person team
- 이런 수준의 전환은 **재설계** 필요. 이 프레임워크는 이주 경로를 제공하지만 자동 진화는 아니다

### 3. AI 모델의 API 자체 변화
- tool-call 포맷이 바뀌거나 hook API 가 deprecated 되면 Layer 3 코드 자체를 고쳐야 한다
- 이는 framework version 에서 처리 (v1 → v2 migration)

### 4. 자가진화의 drift
- 만약 Layer 4 가 잘못된 방향으로 학습하면?
- 방지책: 모든 자가진화는 **제안만**, **사용자 승인 필수**. 자가 drift 가 자동 적용되지 않는다.
- 탐지: meta-audit 가 학습 품질 지표 모니터링

## 트레이드오프

이 프레임워크는 다음을 의식적으로 감수한다:

| 얻는 것 | 감수하는 것 |
|--------|-----------|
| 장기 drift 저항 | 초기 설정 비용 (훅 등록, 필수 산출물 초기화) |
| 기계적 불변식 | 훅 오버헤드 (편집당 50-300ms × 훅 수) |
| 실패 축적 학습 | events.jsonl 누적 (rotate 로 관리) |
| 필수 산출물 강제 | trivial 변경에도 최소한의 문서 갱신 필요 |
| Actor crossover | 혼자 작업 시 secondary reviewer 필요 (또는 사용자가 역할) |

## 성공 기준

이 프레임워크가 성공했다고 볼 수 있는 시점:

1. **Month 1**: 첫 사용자가 훅 차단에 "이번엔 생략" 시도했지만 기계가 막았고, 결과적으로 버그를 발견
2. **Month 3**: Layer 4 가 자동 생성한 skill 초안을 사용자가 승인해서 `_evolving/` 에 추가
3. **Month 6**: Tier 임계값 자동 튜닝 제안이 실제 프로젝트 성장에 맞춰 조정됨
4. **Year 1**: Framework v1 → v2 migration 이 매끄럽게 수행됨. 과거 events/learnings 는 그대로 보존
5. **Year 2**: `memory/project-profile.md` 가 이 프로젝트만의 고유 패턴을 정확히 반영

## 영감 원천

| 프레임워크 | 가져온 것 |
|----------|---------|
| [gstack](https://github.com/garrytan/gstack) | Workflow skills 카탈로그, SKILL.md 템플릿, LLM-as-judge |
| Manta 프레임워크 | 5-stage pipeline, role manifest, 필수 산출물 6개, Python hooks |
| v3 (Claude↔Codex harness) | 10 gates mechanical enforcement, actor crossover, append-only, FAILURE_TAXONOMY |
| [hermes-agent](https://github.com/NousResearch/hermes-agent) | Self-improving learning loop, autonomous skill creation, insights engine |

## 한 줄 요약

> **"AI 가 삐뚤어질 때 브레이크가 작동하고, 시간이 지나도 적응하며, 사용자가 주도권을 유지한다."**
