# Codex Harness v4

Codex Harness v4는 v2를 기반으로 만든 `creative-daily` 템플릿입니다. 목표는 Codex를 평소 자연어 개발에 쓰면서도 두 가지 약점을 줄이는 것입니다.

- 코드 작업에서 LLM이 가정을 숨기거나 과잉 설계하는 문제
- UI/UX 작업에서 그럴듯하지만 평범하고 검증이 약한 결과를 내는 문제

v4는 v3처럼 strict/high-trust 운영을 더 무겁게 만드는 템플릿이 아닙니다. v2의 장기운영 하네스 위에 Karpathy식 엔지니어링 규율과 UI/UX design intelligence를 더한 daily-driver입니다.

## 생성 의도

v4의 생성 의도는 다음과 같습니다.

- 자연어로 지시해도 Codex가 먼저 가정, 단순한 해결책, 검증 기준을 잡게 한다.
- 불필요한 추상화, drive-by refactor, 과도한 프레임워크화를 줄인다.
- UI/UX 작업에서는 design system, accessibility, responsive, interaction state, anti-pattern review를 기본 루프로 만든다.
- v3의 HMAC/strict 운영 마찰 없이, 평소 앱 개발과 프론트엔드 작업 품질을 끌어올린다.

## 참고한 레퍼런스

- `forrestchang/andrej-karpathy-skills`: Think before coding, simplicity first, surgical changes, goal-driven execution.
- `nextlevelbuilder/ui-ux-pro-max-skill`: UI/UX skill auto-activation, design-system generation, stack-specific design guidance, pre-delivery anti-pattern checks.
- OpenAI Codex use cases: skills, long-horizon work, frontend design, PR review, automations, browser/computer use를 Codex-native workflow로 활용.

## v2 / v3 / v4 차이

| 버전 | 목적 | 추천 상황 |
| --- | --- | --- |
| v2 | 안정적인 평소 Codex daily driver | 일반 앱 개발, 장기 개인 프로젝트, 자연어 개발 |
| v3 | strict/high-trust 운영 | 결제, 인증, 보안, production, 2인 협업, 감사 필요 |
| v4 | creative-daily + simplicity + UI/UX | 제품 UI, 프론트엔드, SaaS/landing/dashboard, 과잉구현 방지 |

## 핵심 추가 요소

### Karpathy Engineering

`.agents/skills/karpathy-engineering`은 다음을 강제합니다.

- 가정 명시
- 가장 단순한 해결책 우선
- 필요한 파일만 수정
- 성공 기준을 테스트/검증 가능한 형태로 변환
- 구현 후 모든 변경 라인이 요청과 연결되는지 확인

관련 gate:

```bash
python3 scripts/harness/simplicity_gate.py --template
python3 scripts/harness/harness.py simplicity --template
```

### UI/UX Design Intelligence

`.agents/skills/ui-ux-design`은 UI 작업에서 다음을 요구합니다.

- `UI-UX-Brief.md`
- `Design-System.md`
- `UI-Review.md`
- 접근성, 터치 타깃, 반응형, typography/color token, form feedback, motion, performance 점검

관련 gate:

```bash
python3 scripts/harness/design_gate.py --template
python3 scripts/harness/harness.py design --template
```

## 기본 Workflow

1. 사용자가 자연어로 작업을 요청합니다.
2. Codex가 `trivial`, `normal`, `high-risk`를 분류합니다.
3. 코드 작업이면 `karpathy-engineering` 기준으로 가정, 단순 경로, 검증 기준을 잡습니다.
4. UI/UX 작업이면 `ui-ux-design` 기준으로 design brief와 design system을 먼저 잡습니다.
5. 필요한 경우 read-only subagent를 사용해 mapping, docs, product planning, review를 병렬화합니다.
6. 구현은 main thread 또는 명시적 write scope를 가진 bounded worker가 수행합니다.
7. 완료 전에 gate, quality, simplicity, design, review, session close를 확인합니다.

## 검증

```bash
python3 scripts/harness/bootstrap.py
python3 scripts/harness/self_test.py
python3 -m unittest discover -s tests -q
python3 scripts/harness/score.py --min-score 95
python3 scripts/harness/session_close.py --tier high-risk --template --json
```

## 운영 보조 명령

```bash
python3 scripts/harness/harness.py check --tier normal --template
python3 scripts/harness/harness.py simplicity --template
python3 scripts/harness/harness.py design --template
python3 scripts/harness/review_gate.py prepare --tier normal --producer main-codex
python3 scripts/harness/review_gate.py finalize --review-file harness/reviews/review-YYYYMMDDTHHMMSSZ.md
python3 scripts/harness/subagent_planner.py plan --role worker --owner worker-ui --goal "UI slice" --write-scope src/app --claim
python3 scripts/harness/event_log.py verify
python3 scripts/harness/score.py --min-score 95
```

## 의도대로 잘 작동하는가

템플릿 레벨에서는 다음 방식으로 작동 여부를 확인합니다.

- `self_test.py`가 v4 필수 skill, scripts, templates, docs를 확인합니다.
- `simplicity_gate.py`가 단순성/검증 artifact를 확인합니다.
- `design_gate.py`가 UI/UX artifact와 핵심 섹션을 확인합니다.
- `score.py`와 CI가 기존 v2 하네스 무결성에 v4 gate를 추가로 검사합니다.

실전에서 잘 작동하는지는 `docs/ai/current/`에 실제 artifact를 남기고, 변경 diff가 작고 명확해졌는지, UI 리뷰에서 접근성/반응형/상태 검증이 반복적으로 잡히는지로 판단해야 합니다.

## 약점

- Skill selection은 여전히 Codex의 의도 분류에 의존합니다.
- `simplicity_gate.py`는 artifact 품질을 구조적으로 검사할 뿐, 실제 코드가 정말 단순한지는 완전히 증명하지 못합니다.
- `design_gate.py`는 UI artifact 존재와 섹션 품질을 확인하지만 실제 시각 품질은 browser QA, screenshot review, human taste review가 필요합니다.
- UI/UX Pro Max의 대규모 검색 데이터베이스를 통째로 내장하지 않았기 때문에 추천 폭은 원본 skill보다 좁습니다.
- v4는 strict 보안/감사용 템플릿이 아닙니다. 고위험 production은 v3가 더 적합합니다.

## 강점 극대화 방법

- UI 작업에는 항상 `UI-UX-Brief.md`와 `Design-System.md`를 먼저 작성합니다.
- 구현 뒤에는 browser QA 또는 screenshot review를 실행합니다.
- 반복되는 UI 패턴은 proposed skill로 승격하고 `skillify_audit.py`를 통과시킵니다.
- 큰 refactor에는 `Simplicity-Review.md`를 required로 두고, 작은 작업에는 optional로 둡니다.
- 실제 프로젝트에 디자인 시스템이 생기면 `harness/design/design-system/MASTER.md`로 장기 보관합니다.

## 더 참고할 리소스

- OpenAI Codex use cases: frontend design, PR review, skills, automations, long-horizon tasks.
- WCAG accessibility guidelines.
- Apple Human Interface Guidelines.
- Material Design.
- Refactoring by Martin Fowler.
- A Philosophy of Software Design by John Ousterhout.
- Storybook and visual regression testing for component systems.
