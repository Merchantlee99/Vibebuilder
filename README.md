# Vibebuilder Packs

공유 가능한 바이브코딩 하네스 템플릿 팩을 모아둔 저장소다. 각 팩은 특정 에이전트 앱의 실제 작업 표면과 운영 방식에 맞춰 설계되어 있고, 그대로 복사해 새 프로젝트의 출발점으로 쓰는 것을 전제로 한다.

## 무엇을 위한 저장소인가

- 장기 프로젝트에서 프롬프트 한 번으로 끝나지 않는 작업 흐름을 안정적으로 반복하기 위한 템플릿 저장소다.
- `문서 기반 맥락`, `검증 루프`, `리뷰 규율`, `학습 로그`, `자가진화 제안`을 패키지 형태로 재사용하려는 목적이다.
- 특정 모델의 일반적 성향이 아니라 실제 앱이 제공하는 기능 표면에 맞춰 하네스를 나눴다.

## 포함된 팩

| Pack | 대상 | 핵심 초점 |
|------|------|-----------|
| `vb-pack-claude-harness` | Claude Code 단독 운용 | hook 중심 통제, actor crossover, 강한 기계 차단 |
| `vb-pack-codex-harness` | Codex app 단독 운용 초기 버전 | subagents, automations, modes, browser/computer use를 1급 primitive로 사용 |
| `vb-pack-codex-harness-v2` | Codex app 평소 개발용 | 자연어 daily driver, subagent ownership, review gate, telemetry, quality gate |
| `vb-pack-codex-harness-v3` | Codex app 고신뢰 strict 운용 | hooks-on profile, strict gate, high-risk HMAC review, team/production 운영 기준 |
| `vb-pack-codex-harness-v4` | Codex app creative-daily 운용 | v2 기반에 Karpathy식 단순성 규율과 UI/UX design gate를 추가 |
| `vb-pack-codex-harness-v5` | Codex app evidence-first 운용 | v2/v3/v4 강점을 보존하고 task profile, runtime/UI evidence, static frontend audit, reviewed self-improvement를 추가 |
| `vb-pack-codex-harness-v6` | Codex app intent-routed spec/evidence 운용 | 자연어 요청을 intent route로 기록하고, domain language, spec, REQ evidence, team-rule mining, gstack workflow를 route-selected gate로 연결 |
| `codex-skill` | Codex plugin/skill router 예시 | 자동 라우팅, constraint 보존, skill handoff, route fixture/eval, Mermaid diagram이 포함된 repo-local Codex Skill 패키지 |

## 어떤 레퍼런스를 참고했는가

- [gstack](https://github.com/garrytan/gstack): workflow catalog와 역할별 작업 흐름
- [agents.md](https://github.com/agentsmd/agents.md): agent contract와 역할 경계
- [pm-skills](https://github.com/phuryn/pm-skills): 기획, 요구사항, validation discipline
- [hermes-agent](https://github.com/NousResearch/hermes-agent): learning↔action feedback, skill auto-gen, 장기 적응 루프
- [andrej-karpathy-skills](https://github.com/forrestchang/andrej-karpathy-skills): hidden assumption, overengineering, broad edit를 줄이는 엔지니어링 규율
- [ui-ux-pro-max-skill](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill): UI/UX skill activation, design-system-first workflow, accessibility/responsive/anti-pattern review
- [OpenAI Skills](https://github.com/openai/skills): 반복 가능한 agent workflow를 skill package로 나누는 구조
- [intent-spec-layer](https://github.com/philo-kim/intent-spec-layer): `docs/`와 `spec/`를 분리하고, L0/L1/L2/L3 spec, EARS, REQ ID, evidence mapping으로 intent를 구현 검증에 연결하는 방향
- Cursor/Claude Code rule, skill, hook, command pack 흐름: 큰 단일 규칙 파일보다 focused rule, task-specific skill, deterministic gate를 조합하는 방식

## 버전별 설계 관점

| 흐름 | 질문 | 하네스가 강화하는 것 |
|------|------|----------------------|
| v2 | "일반 구현 작업을 안정적으로 끝냈는가?" | plan, scoped implementation, review, telemetry |
| v3 | "실패 비용이 큰 작업을 엄격하게 통제했는가?" | strict profile, high-risk gate, HMAC review, production/team policy |
| v4 | "과잉구현과 UI/UX 흔들림을 줄였는가?" | simplicity review, UI/UX brief, design gate |
| v5 | "완료라고 말할 증거가 있는가?" | task profile, implementation evidence, runtime/UI evidence, frontend static audit |
| v6 | "이 작업은 어떤 intent/spec/team rule/evidence 기준으로 구현되어야 하는가?" | natural-language intent routing, domain language, L1/L2/L3 spec, REQ evidence, team-rule proposal, gstack workflow |

v6는 v5의 evidence-first 완료 계약을 버리지 않는다. 대신 그 앞단에 `Intent-Routing.json`을 두어 Codex가 자연어 요청을 어떤 작업 모드, 위험도, spec depth, evidence gate, team-rule 검토로 처리할지 먼저 기록하게 만든다.

## 어떤 기대효과를 노리는가

- 작업이 길어져도 채팅창이 아니라 파일과 로그 기준으로 재개할 수 있다.
- 사소한 수정과 고위험 변경을 같은 방식으로 다루지 않고, tier에 맞는 준비와 검증을 요구할 수 있다.
- 반복 실수와 반복 성공을 `learnings`와 `proposed skills`로 축적해 시간이 지나도 운영 품질이 떨어지지 않게 만든다.
- 특정 세션의 즉흥성보다 재현 가능한 작업 방식과 검증 흐름을 남길 수 있다.
- 상위 버전으로 갈수록 "규칙을 많이 넣는 것"이 아니라 "필요한 순간에 필요한 gate만 route하는 것"을 목표로 한다.
- v6는 grill-me / grill-with-docs, PM framing, gstack workflow, intent spec, REQ evidence를 묶어 자연어 요청을 구현 가능한 계약으로 바꾸는 데 초점을 둔다.
- `codex-skill`은 v6보다 좁다. 전체 하네스가 아니라 Codex plugin + skill + 자동 라우팅 + fixture/eval을 한 폴더에서 이해하고 복사할 수 있게 만든 reference package다.

## 어떤 팩을 고르면 되는가

- Claude Code에서 강한 훅 차단과 자기승인 방지가 우선이면 `vb-pack-claude-harness`가 맞다.
- Codex app의 `subagents`, `automations`, `local/worktree/cloud`, `browser`, `computer use`를 실전 primitive로 쓰는 기본 구조를 보고 싶으면 `vb-pack-codex-harness`가 맞다.
- 개인 바이브코딩, 일반 앱 개발, 장기 프로젝트의 평소 운영에는 `vb-pack-codex-harness-v2`가 맞다.
- 결제, 인증/권한, 보안, 금융/트레이딩, DB migration, production 배포, 2인 협업처럼 실패 비용이 큰 작업에는 `vb-pack-codex-harness-v3`가 맞다.
- 제품 UI, 프론트엔드, 랜딩페이지, SaaS/dashboard, 디자인 시스템, 과잉구현 방지가 중요한 daily 작업에는 `vb-pack-codex-harness-v4`가 맞다.
- 구현 성능을 유지하면서 UI/runtime evidence, high-risk strictness, frontend static audit, reviewed self-improvement까지 한 번에 요구하려면 `vb-pack-codex-harness-v5`가 맞다.
- 자연어 요청을 Codex가 스스로 route하고, 행동 변경을 spec/REQ/evidence/team-rule 기준으로 관리해야 한다면 `vb-pack-codex-harness-v6`가 맞다.
- Codex plugin과 skill 구조 자체, 자동 라우터, route fixture/eval, README 다이어그램을 보고 싶으면 `codex-skill`이 맞다.
- 실사용 기준으로는 단순 daily driver는 v2, 고위험 strict 운영은 v3, UI/제품 빌드 중심은 v4, evidence-first 완료 계약은 v5, intent/spec 기반 제품 개발 운영은 v6를 선택하는 흐름을 권장한다.

## v6를 선택해야 하는 경우

`vb-pack-codex-harness-v6`는 아래 상황에 맞다.

- 사용자는 자연어로만 지시하고, Codex가 알아서 적절한 gate와 skill을 선택해야 한다.
- "바로 구현"보다 "무엇을 구현해야 하는지"의 언어, 상태, 권한, 예외, 완료 기준이 더 중요하다.
- 팀이 남긴 코드, 문서, 리뷰, 테스트 흔적을 읽고 반복 규칙을 제안하되, 검수 없이 `AGENTS.md`에 자동 반영하면 안 된다.
- UI, runtime, strict evidence뿐 아니라 spec drift, REQ-to-evidence mapping, domain language까지 남겨야 한다.
- PM skill, gstack workflow, grill-me/grill-with-docs, Hermes-style self-improvement를 하나의 Codex pack 안에서 운용하고 싶다.

v6가 항상 최선은 아니다. 작은 개인 프로젝트에서 마찰 없이 빠르게 구현하는 것이 목표라면 v2/v4가 더 가볍다. v6는 작업 의도와 팀 규칙, spec/evidence 추적이 장기 품질에 영향을 주는 프로젝트에 더 적합하다.

## 시작점

- Claude pack 소개: [vb-pack-claude-harness/README.md](./vb-pack-claude-harness/README.md)
- Codex pack 소개: [vb-pack-codex-harness/README.md](./vb-pack-codex-harness/README.md)
- Codex v2 pack 소개: [vb-pack-codex-harness-v2/README.md](./vb-pack-codex-harness-v2/README.md)
- Codex v3 strict pack 소개: [vb-pack-codex-harness-v3/README.md](./vb-pack-codex-harness-v3/README.md)
- Codex v4 creative-daily pack 소개: [vb-pack-codex-harness-v4/README.md](./vb-pack-codex-harness-v4/README.md)
- Codex v5 evidence-first pack 소개: [vb-pack-codex-harness-v5/README.md](./vb-pack-codex-harness-v5/README.md)
- Codex v6 intent-routed spec/evidence pack 소개: [vb-pack-codex-harness-v6/README.md](./vb-pack-codex-harness-v6/README.md)
- Codex Skill plugin/router 예시: [codex-skill/README.md](./codex-skill/README.md)
