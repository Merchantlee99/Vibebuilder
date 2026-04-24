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

## 어떤 레퍼런스를 참고했는가

- [gstack](https://github.com/garrytan/gstack): workflow catalog와 역할별 작업 흐름
- [agents.md](https://github.com/agentsmd/agents.md): agent contract와 역할 경계
- [pm-skills](https://github.com/phuryn/pm-skills): 기획, 요구사항, validation discipline
- [hermes-agent](https://github.com/NousResearch/hermes-agent): learning↔action feedback, skill auto-gen, 장기 적응 루프

## 어떤 기대효과를 노리는가

- 작업이 길어져도 채팅창이 아니라 파일과 로그 기준으로 재개할 수 있다.
- 사소한 수정과 고위험 변경을 같은 방식으로 다루지 않고, tier에 맞는 준비와 검증을 요구할 수 있다.
- 반복 실수와 반복 성공을 `learnings`와 `proposed skills`로 축적해 시간이 지나도 운영 품질이 떨어지지 않게 만든다.
- 특정 세션의 즉흥성보다 재현 가능한 작업 방식과 검증 흐름을 남길 수 있다.

## 어떤 팩을 고르면 되는가

- Claude Code에서 강한 훅 차단과 자기승인 방지가 우선이면 `vb-pack-claude-harness`가 맞다.
- Codex app의 `subagents`, `automations`, `local/worktree/cloud`, `browser`, `computer use`를 실전 primitive로 쓰는 기본 구조를 보고 싶으면 `vb-pack-codex-harness`가 맞다.
- 개인 바이브코딩, 일반 앱 개발, 장기 프로젝트의 평소 운영에는 `vb-pack-codex-harness-v2`가 맞다.
- 결제, 인증/권한, 보안, 금융/트레이딩, DB migration, production 배포, 2인 협업처럼 실패 비용이 큰 작업에는 `vb-pack-codex-harness-v3`가 맞다.
- 실사용 기준으로는 v2를 기본값으로 두고, 고위험 프로젝트에서만 v3를 선택하는 흐름을 권장한다.

## 시작점

- Claude pack 소개: [vb-pack-claude-harness/README.md](./vb-pack-claude-harness/README.md)
- Codex pack 소개: [vb-pack-codex-harness/README.md](./vb-pack-codex-harness/README.md)
- Codex v2 pack 소개: [vb-pack-codex-harness-v2/README.md](./vb-pack-codex-harness-v2/README.md)
- Codex v3 strict pack 소개: [vb-pack-codex-harness-v3/README.md](./vb-pack-codex-harness-v3/README.md)
