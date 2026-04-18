# Codex Native Harness

Codex app 단독 사용을 전제로 만든 장기 프로젝트용 바이브코딩 하네스다. 기존 Claude 전용 하네스의 장점 중 유지할 것은 `문서 기반 맥락`, `append-only telemetry`, `tier x complexity`, `meta-audit`이고, 버린 것은 `Claude hook 중심 통제`와 `수동 reviewer bridge`다.

## 한눈에 보기

이 팩은 Codex app 자체를 운영 환경으로 놓고, 그 안의 서브 기능을 하네스 규칙으로 엮어 장기 프로젝트를 안정적으로 끌고 가기 위해 만들어졌다. 핵심 목표는 세 가지다.

- Codex app 단독으로도 `subagents`, `automations`, `local/worktree/cloud`, `built-in git`, `integrated terminal`, `browser`, `computer use`를 상황에 맞게 잘 쓰게 만드는 것
- 비사소한 작업을 문서, 플랜, 리뷰, 텔레메트리 기준으로 누적시켜 세션이 바뀌어도 작업 품질이 무너지지 않게 만드는 것
- 반복 실패와 반복 성공을 `learning -> action -> proposed skill` 루프로 연결해 시간이 지나도 스스로 운영 품질을 높이게 만드는 것

## 어떤 문제를 풀기 위해 만들었는가

Codex app은 자체 기능 표면이 강하다. 대신 이 기능들을 언제 써야 하는지, 어떤 순서로 결합해야 하는지, 장기 작업에서 어떤 상태를 파일로 남겨야 하는지에 대한 운영 프레임은 기본 제공되지 않는다. 이 하네스는 그 공백을 메운다.

- 단순 프롬프트 운영이 아니라 `문서 + 상태 파일 + planner scripts + review gate` 조합으로 작업을 관리한다.
- Codex의 native capability를 직접 반영한다. 즉, Claude용 훅 프레임을 억지로 이식하지 않고 Codex의 실제 작업 방식에 맞춘다.
- 템플릿 저장소와 실제 프로젝트 인스턴스를 분리해, 공유용 템플릿이 과도한 enforcement로 오작동하지 않게 한다.

## 기본 설정 철학

- 기본 배포 상태는 `deployment_profile=template`, `mode=advisory` 다.
- 실제 프로젝트에 복제한 뒤 `bootstrap.py --adopt-project --init-git --seed-empty-commit` 으로 `project` 프로파일로 전환하는 것을 기준으로 한다.
- worker 성격의 구현 작업은 기본적으로 `worktree` 를 우선 추천한다.
- follow-up과 continuity는 `heartbeat` automation을 기본으로 둔다.
- review는 사람 리뷰든 reviewer subagent든 같은 artifact 구조와 독립성 메타데이터를 요구한다.
- hook adapter는 공식 surface가 있을 때만 보조적으로 쓰고, 핵심 enforcement는 여전히 스크립트와 문서 flow가 맡는다.

## 참고한 레퍼런스

이 하네스는 하나의 프레임워크를 그대로 가져온 것이 아니라, 네 가지 레퍼런스에서 강한 부분만 재조합해 Codex용으로 다시 설계한 결과물이다. 기본 골격은 아래 세 레퍼런스에서 가져오고, 장기 적응 루프는 `hermes-agent`에서 보강했다.

- `gstack`: workflow catalog와 역할별 작업 흐름.
- `agents.md`: 에이전트 계약서 형식과 역할 경계.
- `pm-skills`: 기획, 요구사항, validation discipline.

Codex 전용 확장은 아래 다섯 축이다.

- `subagents`: bounded parallelism의 기본 엔진.
- `modes`: `local / worktree / cloud`를 작업 격리의 1급 개념으로 취급.
- `automations`: 장기 작업 continuity와 주기 점검.
- `browser + computer use`: 조사, QA, GUI escalation.
- `built-in git + terminal`: 결정론적 검증과 상태 관찰.

추가로 `hermes-agent`에서 참고한 장기 유지 레이어를 넣는다.

- `learning -> action prefetch`: 최근 learnings를 다음 작업 전에 불러온다.
- `sync-from-events`: 반복 실패를 learning log로 승격한다.
- `skill auto-gen`: 반복 패턴이 쌓이면 proposed skill을 자동 초안화한다.
- `insights report`: 이벤트/학습/제안 skill의 추세를 주기적으로 문서화한다.

## 기대효과

- 장기 프로젝트에서 세션이 바뀌어도 `Prompt.md`, `Plan.md`, `Documentation.md`, telemetry를 기준으로 안정적으로 재개할 수 있다.
- Codex의 subagent와 automation을 즉흥적으로 쓰는 대신 planner를 통해 구조화해서 병렬 작업 충돌과 follow-up 누락을 줄일 수 있다.
- review를 선택 사항이 아니라 completion gate에 가깝게 다뤄, self-review completion 같은 약한 종료 패턴을 줄일 수 있다.
- 반복되는 문제를 단순 회고에서 끝내지 않고 `learnings`, `insights`, `proposed skills`로 승격시켜 운영 체계를 점진적으로 개선할 수 있다.
- 템플릿 저장소는 안전하게 배포하고, 실제 프로젝트에서만 더 강한 운영 모드로 승격하는 분리 모델을 유지할 수 있다.

## 누가 쓰면 맞는가

- Codex app 하나로 기획, 구현, 검증, follow-up까지 운영하고 싶은 사람
- 장기 프로젝트에서 subagents와 automations를 실제 운영 primitive로 쓰고 싶은 사람
- 대형 작업을 문서와 검증 기준으로 끌고 가고 싶지만, Claude용 강한 hook enforcement를 그대로 가져오고 싶지는 않은 사람

이번 하드닝에서 추가한 것은 세 가지다.

- `filesystem activity bridge`: Codex app 내부 훅이 없어도 핵심 산출물 변경을 telemetry로 자동 sync한다.
- `independent review metadata`: review artifact에 reviewer/producer/session을 강제해 self-review completion을 막는다.
- `git/worktree bootstrap`: `bootstrap.py --init-git --seed-empty-commit` 또는 `worktree_manager.py init-repo --seed-empty-commit` 으로 실전 진입을 빠르게 만든다.

템플릿 안전장치도 추가했다.

- 템플릿 저장소의 기본 `deployment_profile`은 `template` 이고, 이 상태에서는 `enforced` 승격이 차단된다.
- 실제 프로젝트로 복제한 뒤 `bootstrap.py --adopt-project` 를 실행해야 `project` 프로파일로 전환된다.
- `project` 프로파일에서도 `enforced` 는 git 초기화와 첫 커밋이 있어야만 허용된다.
- repo-local hook adapter는 함께 제공되지만 템플릿에서는 비활성 상태로 시작한다.

## Directory Layout

```text
.
├── AGENTS.md
├── README.md
├── ETHOS.md
├── Prompt.md
├── PRD.md
├── Plan.md
├── Implement.md
├── Documentation.md
├── Subagent-Manifest.md
├── Automation-Intent.md
├── .codex/
│   ├── runtime.json
│   ├── context/
│   ├── telemetry/
│   ├── manifests/
│   ├── reviews/
│   ├── audits/
│   └── playbooks/
├── templates/
└── scripts/harness/
```

## Operating Model

1. 메인 Codex 세션은 orchestrator 역할을 맡는다.
2. `trivial`이 아니면 `Prompt.md`부터 `Plan.md`까지 맥락을 먼저 고정한다.
3. 병렬화가 유효하면 `Subagent-Manifest.md`에 역할과 write scope를 선언한다.
4. 실제 subagent 투입 전에는 `subagent_planner.py`로 dispatch spec과 ownership claim을 만든다.
5. 장기 추적이 필요하면 `automation_planner.py scan`으로 heartbeat 후보를 만든 뒤 실제 automation으로 승격한다.
6. 구현은 기본적으로 `worker -> worktree`, 검증은 `reviewer` 또는 메인 세션에서 수행한다.

## First Run

```bash
python3 scripts/harness/bootstrap.py
python3 scripts/harness/self_test.py
python3 -m unittest discover -s tests -q
```

실제 worktree 병렬 작업까지 바로 열려면:

```bash
python3 scripts/harness/bootstrap.py --adopt-project --init-git --seed-empty-commit
```

예상 결과:

- bootstrap: required dirs/logs ensured
- self-test: core structure green
- unit tests: `OK`

## Core Files

- `AGENTS.md`: Codex가 따를 운영 규칙.
- `ETHOS.md`: 왜 이런 tradeoff를 택했는지에 대한 장기 철학.
- `Automation-Intent.md`: follow-up automation strategy and durable prompt contract.
- `.codex/manifests/*.yaml`: capability routing, subagent policy, mode policy, review matrix, automation policy.
- `.codex/playbooks/*.md`: 실전 운용 플레이북.
- `templates/*.md`: 새 프로젝트 또는 새 epic 시작 시 복제하는 문서 템플릿.
- `scripts/harness/*.py`: 텔레메트리, bootstrap, audit, mode recommendation, review digest.
- `scripts/harness/subagent_planner.py`: subagent dispatch spec, ownership check, claim.
- `scripts/harness/automation_planner.py`: pending review / insights / proposed skill based automation suggestions.
- `scripts/harness/activity_bridge.py`: 파일 변경을 append-only telemetry로 동기화.
- `scripts/harness/memory_feedback.py`, `skill_auto_gen.py`, `insights_report.py`: hermes-inspired Layer 4.

## Design Decisions

- Hook 대신 파일 기반 state와 runbook 중심으로 설계했다.
- `worktree-first`를 worker 기본값으로 둬서 병렬 작업 충돌을 줄였다.
- `review`는 사람이 하든 subagent가 하든 동일한 artifact와 checklist를 요구한다.
- undocumented app hook 대신 filesystem bridge를 넣어 Codex 앱 단독 운용에서도 telemetry 공백을 줄였다.
- `automation`은 부가 기능이 아니라 장기 continuity layer다.
- subagent와 automation은 planner 스크립트로 구조화해 Codex가 더 안정적으로 판단하게 만들었다.

## Current Scope

현재 레포는 Codex 전용 하네스 템플릿 자체를 구현하는 상태다. 실제 다른 프로젝트에 이식할 때는 `Prompt.md`와 `PRD.md`만 바꾸고 나머지 골격을 재사용하면 된다.

## Template vs Project

- 템플릿 저장소: `deployment_profile=template`, `mode=advisory`
- 복제된 실제 프로젝트: `bootstrap.py --adopt-project --init-git --seed-empty-commit` 후 `deployment_profile=project`
- `enforced` 승격: 복제된 프로젝트에서만, git repo와 첫 커밋이 있을 때만 허용

## Review Gate Flow

완료 직전 review gate는 아래 두 단계로 쓰는 것을 기준으로 한다.

```bash
python3 scripts/harness/review_gate.py prepare --tier normal --producer main-codex
python3 scripts/harness/review_gate.py finalize --tier normal --review-file latest
```

- `prepare`: `.codex/reviews/review-<ts>.md` 를 만들고 `Implement.md`의 `## Validation`, `Plan.md`의 `## Rollback`을 가능한 범위에서 채워 넣는다.
- reviewer 는 생성된 review file에서 placeholder 를 실제 값으로 치환하고 `Verdict: accept` 까지 채운다.
- `finalize`: placeholder, self-review, 빈 섹션, non-accept verdict 를 모두 막는다.

## Subagent And Automation Flow

실전 병렬화와 follow-up 판단은 아래 보조기 스크립트를 기준으로 한다.

```bash
python3 scripts/harness/subagent_planner.py plan --role worker --owner worker-auth --goal "auth slice" --write-scope src/auth --write-scope tests/auth --claim
python3 scripts/harness/automation_planner.py scan
```

- `subagent_planner.py`: role purpose, recommended mode, ownership conflict, dispatch prompt를 한 번에 만든다.
- `automation_planner.py`: pending review, evolution sweep, proposed skill triage 후보를 `.codex/context/automation-intents.json`에 기록한다.

## Optional Hook Adapter

공식 Codex hooks surface를 쓰는 repo-local adapter도 포함했다.

1. `bootstrap.py --adopt-project --init-git --seed-empty-commit` 로 project profile 전환
2. `~/.codex/config.toml` 에 아래 feature flag 추가

```toml
[features]
codex_hooks = true
```

3. Codex app/CLI 재시작

제공되는 hook:

- `SessionStart`: 현재 harness 상태와 review flow를 짧게 주입
- `UserPromptSubmit`: 관련 learnings prefetch
- `PostToolUse(Bash)`: artifact sync
- `Stop`: 준비된 review artifact가 미완료면 한 번 더 continuation

이 adapter는 보조 레이어다. 핵심 enforcement는 계속 `runtime_gate.py` 와 `review_gate.py` 가 담당한다.
