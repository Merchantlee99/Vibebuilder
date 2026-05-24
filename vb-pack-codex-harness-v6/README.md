# Codex Harness v6

Codex Harness v6는 자연어 요청을 `intent route`, `domain language`, `spec`, `REQ evidence`, `team-rule proposal`, `implementation evidence`로 연결하는 Codex 전용 하네스 템플릿입니다.

v6의 핵심은 사용자가 gate 이름을 외우게 만드는 것이 아닙니다. 사용자는 자연어로 말하고, Codex가 내부적으로 작업 경로를 판단한 뒤 `Intent-Routing.json`에 기록합니다. 이후 deterministic gate가 그 판단과 완료 증거를 검증합니다.

```text
v6 = v2 implementation discipline
   + v3 high-risk strictness
   + v4 simplicity and UI/UX discipline
   + v5 implementation/UI/runtime evidence
   + natural-language intent routing
   + grill-me / grill-with-docs
   + intent spec layer
   + REQ-to-evidence bridge
   + gstack workflow catalog
   + reviewed team-rule mining
```

이 저장소는 활성화된 프로젝트 인스턴스가 아니라 템플릿입니다. 실제 프로젝트에 복사한 뒤에는 프로젝트의 스택, UI 표면, 테스트 방식, 팀 규칙, 보안 요구에 맞게 adoption profile과 gate 강도를 조정해야 합니다.

## 생성 의도

v5는 "완료라고 말할 증거가 있는가?"를 강하게 물었습니다. v6는 그 앞에 더 중요한 질문을 추가합니다.

> 이 작업은 어떤 의도, 언어, spec, 팀 맥락, evidence 기준으로 구현되어야 하는가?

v6의 생성 의도는 다음과 같습니다.

- Codex가 자연어 요청을 받았을 때 작업 모드, 위험도, 필요한 spec layer, UI/runtime/strict evidence를 스스로 route하게 합니다.
- `grill-me`와 `grill-with-docs`를 통해 애매한 요구사항, 코드베이스 흔적, 팀 규칙, edge case를 구현 전에 드러냅니다.
- shared nouns, states, ownership, authority, UI vocabulary를 `Domain-Language.md`로 고정합니다.
- behavior change를 L1/L2/L3 spec과 EARS-style `REQ-...` 문장으로 표현하고, 각 REQ를 실제 evidence와 연결합니다.
- 팀이 반복해서 쓰는 규칙은 자동으로 `AGENTS.md`에 승격하지 않고 `Team-Rule-Proposal.md`로 격리합니다.
- Hermes-style 자기개선은 수용하되, raw learning이 바로 active policy가 되지 못하게 review/promotion gate를 둡니다.
- v2/v3/v4/v5의 구현 성능과 strict/evidence 장점을 유지하면서, v6 고유의 intent/spec 앞단을 추가합니다.

## 참고한 레퍼런스

v6는 아래 흐름을 참고했지만, 모든 내용을 그대로 수용하지는 않았습니다. 기준은 `Codex의 구현 성능을 떨어뜨리지 않으면서, 자연어 요청을 구현 가능한 계약으로 바꾸는가`입니다.

- [agents.md](https://github.com/agentsmd/agents.md): agent contract, 프로젝트 지침, 역할 경계.
- [OpenAI Skills](https://github.com/openai/skills): 반복 가능한 agent workflow를 작은 skill package로 분리하는 구조.
- [gstack](https://github.com/garrytan/gstack): workflow catalog와 역할 기반 작업 흐름.
- [pm-skills](https://github.com/phuryn/pm-skills): 제품 framing, acceptance criteria, validation discipline.
- [hermes-agent](https://github.com/NousResearch/hermes-agent): observe, learn, propose, improve로 이어지는 자기개선 루프.
- [andrej-karpathy-skills](https://github.com/forrestchang/andrej-karpathy-skills): hidden assumption, overengineering, broad edit를 줄이는 엔지니어링 규율.
- [ui-ux-pro-max-skill](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill): UI/UX skill activation, design-system-first workflow, accessibility/responsive/anti-pattern review.
- [intent-spec-layer](https://github.com/philo-kim/intent-spec-layer): `docs/`와 `spec/` 분리, L0/L1/L2/L3 spec, EARS, REQ ID, verification mapping.
- grill-me / grill-with-docs 패턴: 작업 전 질문과 기존 문서/코드 기반 반박을 통해 요구사항의 빈칸을 드러내는 방식.

v6가 강하게 수용한 것은 `모든 규칙을 항상 넣는 방식`이 아니라 `작은 always rule + natural-language routing + task-specific skill + deterministic gate + evidence artifact` 조합입니다.

## v2 / v3 / v4 / v5 / v6 차이

| 버전 | 목적 | 추천 상황 | 한계 |
| --- | --- | --- | --- |
| v2 | 안정적인 평소 Codex daily driver | 일반 앱 개발, 장기 개인 프로젝트, 자연어 개발 | UI/runtime evidence가 약함 |
| v3 | strict/high-trust 운영 | 결제, 인증, 보안, production, 2인 협업, 감사 필요 | 운영 마찰이 크고 UI 품질 검증 중심은 아님 |
| v4 | creative-daily + simplicity + UI/UX | 제품 UI, 프론트엔드, SaaS/landing/dashboard, 과잉구현 방지 | UI artifact는 보지만 실제 runtime/visual evidence는 약함 |
| v5 | implementation-first evidence harness | 앱 개발 전반, UI/제품 품질, 고위험 UI, 장기 자기개선 운영 | 구현 완료 증거는 강하지만 구현 전 intent/spec alignment는 약함 |
| v6 | intent-routed spec/evidence harness | 자연어 요청을 spec, REQ, evidence, team-rule 기준으로 관리해야 하는 제품 개발 | 작은 단발 작업에는 문서/gate 마찰이 더 클 수 있음 |

v6는 v5를 대체해서 evidence를 줄이는 버전이 아닙니다. v5의 implementation/UI/runtime/strict evidence를 유지하고, 그 앞단에 intent routing과 spec governance를 추가합니다.

## 핵심 추가 요소

### Intent Routing

`templates/Intent-Routing.json`과 `scripts/harness/intent_router_gate.py`가 자연어 요청을 작업 경로로 바꿉니다.

기록하는 내용:

- task id
- request summary
- mode
- tier
- surface
- grill-me / grill-with-docs 필요 여부
- domain language 필요 여부
- spec 필요 여부와 L1/L2/L3 layer
- team-rule scan 필요 여부
- required gates
- routing reason
- completion rule

`gate.py all --tier normal`은 이제 v6 intent routing을 먼저 실행한 뒤, route가 요구한 spec/evidence/team-rule gate를 실행합니다.

### Grill Me / Grill With Docs

`grill-me`는 아직 코드베이스 맥락이 약하거나 사용자의 의도가 덜 정리된 상태에서 사용합니다.

`grill-with-docs`는 기존 코드, 문서, spec, ADR, test, review, 팀 convention이 있을 때 사용합니다. 이 경우 Codex는 단순히 질문만 하는 것이 아니라 기존 흔적을 보고 충돌, 누락, 암묵 규칙을 찾아야 합니다.

### Domain Language

`Domain-Language.md`는 제품/코드/테스트/UI에서 쓰는 용어를 고정합니다.

포함해야 하는 것:

- canonical terms
- rejected aliases
- entities
- states
- invariants
- open questions

이 파일은 "예쁜 문서"가 아니라 구현 전 shared language를 고정하는 장치입니다.

### Intent Spec Layer

`Feature-Spec.md`는 L0/L1/L2/L3 구조를 사용합니다.

- L0: constitution, 변하지 않는 원칙
- L1: domain truth, 용어와 상태
- L2: behavior spec, EARS-style requirement
- L3: interface contract, ordering/idempotency/partial failure/retry/rollback

L2 behavior는 `REQ-...` 또는 `REQ-...:Sx` 형태의 statement ID를 가져야 합니다.

### REQ Evidence Map

`Req-Evidence-Map.md`는 각 REQ statement를 evidence에 연결합니다.

허용되는 완료 evidence 예:

- executed unit/integration/e2e test
- build/typecheck/lint
- runtime smoke
- UI/layout/accessibility evidence
- guardrail script
- named manual review
- accepted blocked/not-applicable reason

`generated_stub`, `mapped`, `traced`는 completion evidence가 아닙니다. 구현 슬롯일 뿐입니다.

### Team-Rule Mining

`Team-Rule-Proposal.md`는 코드베이스에서 반복되는 팀 규칙을 제안하는 파일입니다.

규칙은 자동으로 active policy가 되지 않습니다. 특히 아래 target은 별도 reviewer approval과 override가 필요합니다.

- `AGENTS.md`
- `.codex/config.toml`
- hooks
- `harness/strict_policy.json`
- auth/billing/deletion/security/public API/design-system global rule

### GStack Workflow Catalog

`gstack/`은 v6의 워크플로 카탈로그입니다.

포함된 workflow:

- `intent-routed-implementation`
- `grill-with-docs-team-rules`
- `ui-evidence-review`
- `high-risk-strict`

GStack은 두 번째 헌법이 아닙니다. `AGENTS.md`, `harness/runtime.json`, `harness/strict_policy.json`와 충돌하면 더 엄격한 정책이 우선입니다.

### Hermes-Style Self-Improvement

자가개선 루프는 다음 순서로 제한됩니다.

```text
observe -> cluster -> diagnose -> propose -> test -> review -> promote -> monitor
```

반복 실수나 반복 성공은 바로 active rule이 되지 않습니다. `memory_guard`, `learning_detector`, `team_rule_mining_gate`, `rule_promotion_gate`를 거쳐야 합니다.

## 기본 Workflow

1. 사용자가 자연어로 작업을 요청합니다.
2. Codex가 `Intent-Routing.json`에 mode, tier, spec layer, required gate, completion rule을 기록합니다.
3. 필요하면 `grill-me` 또는 `grill-with-docs`로 요구사항의 빈칸을 드러냅니다.
4. shared language가 필요하면 `Domain-Language.md`를 작성합니다.
5. behavior change가 있으면 `Feature-Spec.md`와 `Req-Evidence-Map.md`를 작성합니다.
6. 구현은 main thread 또는 명시적 write scope를 가진 bounded worker가 수행합니다.
7. 완료 전 route-selected gate와 v5 계열 implementation/UI/runtime/strict evidence gate를 실행합니다.
8. 반복 팀 규칙은 `Team-Rule-Proposal.md`로 남기고, review 없이는 승격하지 않습니다.

## 주요 명령

v6 gate를 개별 확인합니다.

```bash
python3 scripts/harness/intent_router_gate.py --template --json
python3 scripts/harness/domain_language_gate.py --template --json
python3 scripts/harness/spec_gate.py --template --json
python3 scripts/harness/req_evidence_gate.py --template --json
python3 scripts/harness/team_rule_mining_gate.py --template --json
python3 scripts/harness/rule_promotion_gate.py --template --json
python3 scripts/harness/spec_drift_gate.py --template --json
```

단일 wrapper로 실행합니다.

```bash
python3 scripts/harness/harness.py intent-routing --template --json
python3 scripts/harness/harness.py domain-language --template --json
python3 scripts/harness/harness.py spec --template --json
python3 scripts/harness/harness.py req-evidence --template --json
python3 scripts/harness/harness.py team-rule --template --json
python3 scripts/harness/harness.py rule-promotion --template --json
python3 scripts/harness/harness.py spec-drift --template --json
```

completion gate를 실행합니다.

```bash
python3 scripts/harness/harness.py check --tier normal --template
python3 scripts/harness/gate.py all --tier normal --template --json
```

템플릿 구조 검사를 실행합니다.

```bash
python3 scripts/harness/bootstrap.py
python3 scripts/harness/self_test.py
python3 -m unittest discover -s tests -q
python3 scripts/harness/score.py --min-score 95
```

v5 대비 gate overhead를 확인합니다.

```bash
python3 scripts/harness/benchmark_harness.py \
  --quick \
  --baseline-root ../vb-pack-codex-harness-v5 \
  --output /tmp/v6-benchmark.json \
  --json
```

## 의도대로 잘 작동하는가

템플릿 레벨에서는 다음 방식으로 확인합니다.

- `self_test.py`가 v6 필수 skills, scripts, templates, docs, spec, gstack workflow를 확인합니다.
- `gate.py all`이 intent route를 먼저 검증하고, route-selected spec/evidence/team-rule gate를 completion path에 연결합니다.
- `intent_router_gate.py`가 high-risk route의 strict gate 누락, spec route의 spec/REQ evidence 누락, team-rule route의 proposal gate 누락을 막습니다.
- `spec_gate.py`가 L2 REQ/EARS/[Unwanted] requirement와 L3 ordering/idempotency/partial failure contract를 확인합니다.
- `req_evidence_gate.py`가 generated stub이나 trace-only row를 completion evidence로 인정하지 않습니다.
- `team_rule_mining_gate.py`와 `rule_promotion_gate.py`가 inferred team rule의 무검수 승격을 막습니다.
- v5 계열 `implementation_gate`, `ui_evidence_gate`, `runtime_evidence_gate`, `strict_gate`, `review_gate`는 계속 completion path에 남아 있습니다.

최근 템플릿 검증 기준:

- `self_test.py`: pass
- unittest: 42 tests, pass
- `score.py --min-score 95`: 100/100
- v5 quick benchmark: pass, warning 없음

## 기대할 수 있는 것

- 사용자는 자연어로 요청하고, Codex는 스스로 적절한 route와 gate를 선택할 수 있습니다.
- 구현 전 intent, language, spec, team context가 명확해집니다.
- "요구사항처럼 보이는 말"과 "검증된 구현 계약"을 분리할 수 있습니다.
- UI/runtime evidence를 강화하되, 비 UI 작업에 불필요한 시각 검증을 강제하지 않습니다.
- 팀 규칙은 축적되지만, 검수 없이 always rule을 오염시키지 않습니다.
- v2/v3/v4/v5보다 장기 프로젝트의 재개, 리뷰, spec drift 추적이 쉬워집니다.

## 약점

- v6가 제품 판단을 자동으로 보장하지는 않습니다. Codex가 선택한 route를 파일로 남기고 gate가 검증하게 만드는 구조입니다.
- 작은 단발 수정에는 v6의 spec/routing artifact가 과할 수 있습니다.
- `frontend_static_audit.py`는 heuristic입니다. 실제 computed layout, visual hierarchy, 고객 언어의 적절성은 browser QA와 사람 리뷰가 여전히 필요합니다.
- `implementation_gate.py`와 `req_evidence_gate.py`는 evidence shape를 검증합니다. 테스트가 의미 있게 충분한지는 독립 리뷰와 프로젝트 CI가 판단해야 합니다.
- team-rule mining은 제안까지만 자동화합니다. active policy 승격은 reviewer approval과 promotion gate가 필요합니다.
- HMAC approval은 secret이 Codex 세션 밖에 보관될 때만 강한 승인 증거가 됩니다.
