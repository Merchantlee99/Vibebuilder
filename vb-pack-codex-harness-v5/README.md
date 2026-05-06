# Codex Harness v5

Codex Harness v5는 AI가 만든 제품/소프트웨어 결과물을 `구현 증거`, `런타임 증거`, `UI evidence`, `독립 리뷰`, `자가개선 검수` 기준으로 닫기 위한 Codex 전용 하네스 템플릿입니다.

v5는 v4를 시각 평가 중심으로만 확장한 버전이 아닙니다. v2의 구현 성능, v3의 high-risk strict 운영, v4의 단순성/UI 규율을 보존한 상태에서, 실제 작업 완료를 더 강한 evidence loop로 검증하는 것을 목표로 합니다.

```text
v5 = v2 implementation discipline
   + v3 high-risk strictness
   + v4 simplicity and UI/UX discipline
   + task-profile based routing
   + runtime/UI evidence gate
   + frontend static audit
   + Hermes-style reviewed self-improvement
```

이 저장소는 활성화된 프로젝트 인스턴스가 아니라 템플릿입니다. 실제 프로젝트에 복사한 뒤에는 프로젝트의 스택, UI 표면, 테스트 방식, 보안 요구에 맞게 adoption profile과 gate 강도를 조정해야 합니다.

## 생성 의도

v5의 생성 의도는 다음과 같습니다.

- Codex가 UI를 만들고도 실제 화면, 상태, 정보 밀도, 필요 없는 버튼, 상세 화면 간 규칙, 예외 상태를 충분히 검증하지 못하는 문제를 줄입니다.
- `normal+` 작업에서 구현했다고 주장하려면 test/build/typecheck/runtime 같은 구현 증거를 남기게 합니다.
- UI 작업에서 screenshot-only completion을 막고, route/state/viewport/context가 있는 evidence를 요구합니다.
- CSS/Tailwind/frontend source를 정적으로 훑어 raw color, arbitrary value, token drift, layout-risk hint를 찾습니다.
- v3의 high-risk HMAC/strict 관점을 v5 안에 다시 포함해 UI 작업이라도 결제, 인증, 권한, 삭제, 복원, overwrite 같은 위험 표면은 strict path로 보냅니다.
- Hermes agent식 자기개선 루프를 수용하되, raw learning이 바로 규칙이 되지 못하게 memory proposal, test fixture, review gate로 격리합니다.

## 참고한 레퍼런스

v5는 아래 흐름을 참고했지만, 모든 내용을 그대로 수용하지는 않았습니다. 기준은 `실제 Codex 구현 성능을 떨어뜨리지 않으면서 완료 검증력을 높이는가`입니다.

- [OpenAI Skills](https://github.com/openai/skills): 반복 가능한 agent workflow를 `SKILL.md`, scripts, resources로 쪼개는 구조.
- [agents.md](https://github.com/agentsmd/agents.md): agent contract, 프로젝트 지침, 역할 경계.
- [gstack](https://github.com/garrytan/gstack): workflow catalog와 역할 기반 작업 흐름.
- [hermes-agent](https://github.com/NousResearch/hermes-agent): observe, learn, propose, improve로 이어지는 자기개선 루프.
- [andrej-karpathy-skills](https://github.com/forrestchang/andrej-karpathy-skills): hidden assumption, overengineering, broad edit를 줄이는 단순성 규율.
- [ui-ux-pro-max-skill](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill): UI/UX skill activation, design-system-first workflow, accessibility/responsive/anti-pattern review.
- [awesome-cursorrules](https://github.com/PatrickJS/awesome-cursorrules): 프레임워크별 rule pack이 늘어나는 시장 흐름과 pack template 관점.
- [cursor-best-practices](https://github.com/digitalchild/cursor-best-practices): focused/composable rules, 작은 규칙 파일, task-specific rule 분리.
- [cursor-designer](https://github.com/spencergoldade/cursor-designer): UX, UI, IA, accessibility를 design-first rule로 다루는 방향.
- Claude Code 계열 best-practice / everything-claude-code류 구조: rules, skills, hooks, commands, MCP config를 하나의 pack으로 묶는 방식.

v5가 특히 강하게 수용한 것은 `거대한 단일 규칙 파일`이 아니라 `작은 always rule + task-specific skill + deterministic gate + evidence artifact` 조합입니다.

## v2 / v3 / v4 / v5 차이

| 버전 | 목적 | 추천 상황 | 한계 |
| --- | --- | --- | --- |
| v2 | 안정적인 평소 Codex daily driver | 일반 앱 개발, 장기 개인 프로젝트, 자연어 개발 | UI/runtime evidence가 약함 |
| v3 | strict/high-trust 운영 | 결제, 인증, 보안, production, 2인 협업, 감사 필요 | 운영 마찰이 크고 UI 품질 검증 중심은 아님 |
| v4 | creative-daily + simplicity + UI/UX | 제품 UI, 프론트엔드, SaaS/landing/dashboard, 과잉구현 방지 | UI artifact는 보지만 실제 runtime/visual evidence는 약함 |
| v5 | implementation-first evidence harness | 앱 개발 전반, UI/제품 품질, 고위험 UI, 장기 자기개선 운영 | 실제 프로젝트 adoption과 evidence 수집 루프가 필요 |

v5는 v2/v3/v4를 대체한다기보다, 세 버전의 강점을 하나의 completion contract로 합친 템플릿입니다. 핵심 차이는 "좋은 UI를 만들어라"가 아니라 "좋다고 주장하려면 어떤 증거를 남겼는가"를 묻는다는 점입니다.

## 핵심 추가 요소

### Task Profile Routing

`templates/Task-Profile.json`과 `scripts/harness/task_profile_gate.py`가 작업의 종류, 위험도, 표면, 필요한 gate를 명시합니다.

예를 들어 backend-only 작업은 UI evidence를 요구하지 않아야 하고, destructive UI나 auth/billing은 UI 작업이어도 high-risk strict path로 가야 합니다.

### Implementation Evidence

`scripts/harness/implementation_gate.py`는 `normal+` 작업에서 구현 증거가 없는 완료를 막습니다.

요구하는 증거의 예:

- test command
- build command
- typecheck/lint
- runtime smoke check
- migration dry-run
- 수동 검증 사유와 residual risk

### UI Evidence Gate

`scripts/harness/ui_evidence_gate.py`는 UI 변경에서 screenshot-only completion을 막습니다.

유효한 UI evidence는 다음 정보를 가져야 합니다.

- route
- state
- viewport
- artifact path
- screenshot 또는 no-screenshot rationale
- screenshot 외 evidence: layout, accessibility, runtime, static audit, independent UI review 중 하나 이상

민감 화면은 redacted screenshot 또는 명시적인 no-screenshot reason이 필요합니다.

### Runtime And Non-Web UI Evidence

`runtime_evidence_gate.py`와 `non_web_ui_evidence_gate.py`는 웹 브라우저 화면만 전제로 하지 않습니다. CLI/TUI, desktop, mobile, canvas, native shell 같은 UI도 별도 adapter/manual evidence로 닫을 수 있게 분리했습니다.

### Frontend Static Audit

`frontend_static_audit.py`는 실제 스크린샷 평가를 대체하지 않습니다. 대신 UI가 아쉬울 때 코드 쪽에서 원인을 찾기 위한 보조 분석을 제공합니다.

잡는 신호:

- raw hex/rgb color
- arbitrary Tailwind value
- spacing/radius/text token drift
- absolute/fixed/overflow/z-index layout risk
- 기존 design token이나 component reuse를 우회했을 가능성

### High-Risk Strictness

v5는 v3 strictness를 다시 포함합니다.

- `harness/strict_policy.json`
- `scripts/harness/strict_gate.py`
- high-risk HMAC review approval
- prepared review event, nonce, fingerprint
- strict adoption profile

고위험 review는 정책상 `HARNESS_REVIEW_SECRET` 기반 HMAC approval을 기본 요구합니다. 다만 이 secret이 Codex 세션 밖에 있을 때만 사람 승인 증거로 의미가 있습니다.

### Hermes-Style Self-Improvement

자가개선 루프는 다음 순서로 제한됩니다.

```text
observe -> cluster -> diagnose -> propose -> test -> review -> promote -> monitor
```

반복 실수나 반복 성공은 바로 `AGENTS.md`를 바꾸지 않습니다. `Memory-Proposal.md`, proposed skill, test fixture, independent review를 거쳐야 합니다.

## 기본 Workflow

1. 사용자가 자연어로 작업을 요청합니다.
2. Codex가 `trivial`, `normal`, `high-risk`와 UI/runtime evidence 필요 여부를 분류합니다.
3. `normal+` 작업은 `Task-Profile.json`, plan, validation, rollback 기준을 먼저 고정합니다.
4. UI 작업이면 `UI-UX-Brief.md`, `Design-System.md`, `Visual-Evidence.md` 흐름을 사용합니다.
5. 구현은 main thread 또는 명시적 write scope를 가진 bounded worker가 수행합니다.
6. 완료 전 `implementation_gate`, `ui_evidence_gate`, `runtime_evidence_gate`, `strict_gate`, `review_gate`를 필요한 범위만 실행합니다.
7. 반복 학습은 memory proposal로 격리하고, 검수된 것만 skill/rule로 승격합니다.

## 검증

템플릿 구조 검사를 실행합니다.

```bash
python3 scripts/harness/bootstrap.py
python3 scripts/harness/self_test.py
python3 -m unittest discover -s tests -q
python3 scripts/harness/score.py --min-score 95
```

v4 대비 gate overhead를 확인합니다.

```bash
python3 scripts/harness/benchmark_harness.py \
  --quick \
  --baseline-root ../vb-pack-codex-harness-v4 \
  --output /tmp/v5-benchmark.json \
  --json
```

주요 evidence gate를 개별 실행합니다.

```bash
python3 scripts/harness/task_profile_gate.py template --json
python3 scripts/harness/implementation_gate.py --template --json
python3 scripts/harness/ui_evidence_gate.py --template --json
python3 scripts/harness/runtime_evidence_gate.py --template --json
python3 scripts/harness/strict_gate.py --template --json
python3 scripts/harness/memory_guard.py audit --json
python3 scripts/harness/frontend_static_audit.py --root . --json
```

## 운영 보조 명령

```bash
python3 scripts/harness/harness.py check --tier normal --template
python3 scripts/harness/harness.py check --tier normal --artifact-dir docs/ai/current --review-file harness/reviews/review-YYYYMMDDTHHMMSSZ.md
python3 scripts/harness/review_gate.py prepare --tier high-risk --producer main-codex
python3 scripts/harness/review_gate.py finalize --review-file harness/reviews/review-YYYYMMDDTHHMMSSZ.md --approval-token <hmac-sha256(review_file:nonce)>
python3 scripts/harness/evidence_log.py append --task-id task-settings-ui --kind command --tier normal --status pass --command "pnpm test" --exit-code 0 --summary "Tests passed."
python3 scripts/harness/evidence_log.py verify --json
python3 scripts/harness/session_close.py --tier normal --template --json
```

## 의도대로 잘 작동하는가

템플릿 레벨에서는 다음 방식으로 확인합니다.

- `self_test.py`가 v5 필수 skills, scripts, templates, docs를 확인합니다.
- `gate.py all`이 task profile, implementation, UI evidence, runtime evidence, non-web UI, strict gate를 completion path에 연결합니다.
- `review_gate.py`가 high-risk HMAC approval을 정책 기준으로 강제합니다.
- `ui_evidence_gate.py`가 screenshot-only UI completion과 민감 UI의 unredacted evidence를 막습니다.
- `frontend_static_audit.py`가 코드 수준의 시각 품질 리스크를 보조적으로 드러냅니다.
- `benchmark_harness.py`가 v4와 공통 gate의 지연 증가를 측정해 v5가 구현 성능을 크게 해치지 않는지 확인합니다.

최근 템플릿 검증 기준:

- `self_test.py`: pass
- unittest: 34 tests, pass
- `score.py --min-score 95`: 100/100
- v4 quick benchmark: pass, warning 없음

## 기대할 수 있는 것

- Codex가 "완료했다"고 말하기 전에 어떤 evidence가 있는지 더 선명하게 남습니다.
- UI 작업에서 default 화면만 그럴듯하고 loading/empty/error/sensitive state가 빠지는 문제를 줄일 수 있습니다.
- CSS/frontend 코드에서 design token drift나 layout-risk를 빠르게 찾을 수 있습니다.
- 고위험 작업은 UI 변경이라도 strict review와 HMAC approval 경로로 보낼 수 있습니다.
- 반복 학습은 축적되지만, 검수 없이 규칙 파일을 오염시키지 않습니다.
- v2/v3/v4보다 완료 계약이 구체적이므로 장기 프로젝트 재개와 리뷰가 쉬워집니다.

## 약점

- v5가 좋은 취향을 자동으로 보장하지는 않습니다. 나쁜 UI를 통과시키기 어렵게 만드는 evidence loop입니다.
- Playwright/axe 기반 자동 screenshot capture adapter는 아직 내장되어 있지 않습니다. 현재는 evidence를 기록하고 검증하는 하네스가 중심입니다.
- `frontend_static_audit.py`는 heuristic입니다. 실제 computed layout, visual hierarchy, 고객 언어의 적절성은 browser QA와 사람 리뷰가 여전히 필요합니다.
- `implementation_gate.py`는 evidence shape를 검증합니다. 테스트가 의미 있게 충분한지는 독립 리뷰와 프로젝트 CI가 판단해야 합니다.
- HMAC approval은 secret이 Codex 세션 밖에 보관될 때만 강한 승인 증거가 됩니다.

## 강점 극대화 방법

- UI 작업을 시작할 때 `Task-Profile.json`과 `UI-UX-Brief.md`를 먼저 작성합니다.
- screenshot은 route/state/viewport를 항상 같이 기록합니다.
- screenshot만 남기지 말고 accessibility/runtime/static audit 중 하나 이상을 함께 남깁니다.
- high-risk UI를 normal UI로 처리하지 않습니다. 결제, 인증, 권한, 삭제, overwrite, restore는 strict path로 보냅니다.
- 반복되는 좋은 판단과 실패는 바로 규칙에 넣지 말고 memory proposal로 격리합니다.
- 실제 프로젝트에서는 CI에 `self_test.py`, `score.py`, `gate.py all --tier normal`을 연결합니다.

## 더 참고할 리소스

- OpenAI Codex skills, frontend design, PR review, long-horizon work, automations.
- WCAG accessibility guidelines.
- Apple Human Interface Guidelines.
- Material Design.
- Storybook and visual regression testing.
- Playwright screenshot testing.
- axe-core accessibility testing.
- A Philosophy of Software Design by John Ousterhout.
- Refactoring by Martin Fowler.
