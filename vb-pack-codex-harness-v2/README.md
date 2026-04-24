# Codex Harness v2

Codex Harness v2는 장기적인 제품/소프트웨어 작업을 Codex 단독으로 운영하기 위한 프레임워크입니다. 자연어 사용을 전제로 설계되어 있습니다. 사용자가 목표를 설명하면, Codex는 하네스 규칙에 따라 언제 계획을 세우고, subagent를 띄우고, worktree를 사용하고, 터미널 검증을 실행하고, 브라우저 조사를 수행하고, automation을 제안하며, 독립 리뷰를 요구할지 판단합니다.

이 저장소는 활성화된 프로젝트 인스턴스가 아니라 템플릿입니다. 더 강한 enforcement를 켜기 전에 안전하게 검토하고, 복사하고, 프로젝트에 맞게 조정할 수 있습니다.

## 설계 목표

- Codex native 구조를 유지합니다: `AGENTS.md`, `.codex/config.toml`, `.codex/agents/*.toml`, `.agents/skills`를 사용합니다.
- `AGENTS.md`는 얇고 지시적으로 유지하고, 재사용 가능한 workflow는 skills로 분리합니다.
- `.codex`는 정적 control plane으로 유지하고, 변경 가능한 runtime state는 `harness/`와 `docs/ai/` 아래에 둡니다.
- subagent는 유용하지만 제한적으로 사용합니다. read-only agent는 병렬로 확장할 수 있지만, writing worker는 명시적 ownership과 보통 worktree가 필요합니다.
- 신뢰가 아니라 gate로 완료를 강제합니다: plan gate, scope gate, review gate, finish gate, optional hook/CI 연동을 사용합니다.
- 자연어 운영을 보존합니다. 사용자가 일반 작업 중 명령어를 외울 필요가 없어야 합니다.

## 하네스 레이어

| 레이어 | 파일 | 목적 | 강도 |
| --- | --- | --- | --- |
| Steering | `AGENTS.md` | Codex 기본 행동과 escalation 규칙 | Advisory |
| Native config | `.codex/config.toml` | thread fan-out 제한과 optional hooks | Medium |
| Custom agents | `.codex/agents/*.toml` | 역할별 subagent와 sandbox 기본값 | Medium |
| Skills | `.agents/skills/*/SKILL.md` | 의도에 따라 로드되는 재사용 workflow | Medium |
| Gates | `scripts/harness/gate.py` | 완료 전 결정론적 검사 | Strong |
| Hooks | `.codex/hooks/*.py` | optional 실시간 guardrail | Medium, experimental |
| CI | `scripts/harness/self_test.py` | 저장소 레벨 검증 | Strong |
| Scoring | `scripts/harness/score.py` | 9.5 목표 기준 readiness 측정 | Strong |

## 기본 Workflow

1. 사용자가 자연어로 작업을 요청합니다.
2. main Codex가 orchestrator 역할을 맡고 작업을 `trivial`, `normal`, `high-risk`로 분류합니다.
3. `normal+` 작업에서는 수정 전에 목표, 제약, owner, validation, rollback을 고정합니다.
4. 범위가 넓거나 위험한 작업에서는 먼저 read-only subagent를 사용합니다: 필요에 따라 `pm_strategist`, `docs_researcher`, `code_mapper`, `task_distributor`, red-team agent를 사용합니다.
5. 구현은 main thread 또는 명시적 write scope를 가진 bounded worker가 수행합니다.
6. 완료에는 validation이 필요하며, `normal+` 작업에서는 독립 리뷰 결과가 필요합니다.
7. 반복 실패는 조용한 자기 수정이 아니라 proposed skill로 전환합니다.

## 디렉터리 구조

```text
.
├── AGENTS.md
├── README.md
├── ETHOS.md
├── .codex/
│   ├── config.toml
│   ├── agents/
│   └── hooks/
├── .agents/
│   └── skills/
├── harness/
│   ├── runtime.json
│   ├── context/
│   ├── reviews/
│   ├── telemetry/
│   ├── proposed-skills/
│   └── audits/
├── docs/ai/
├── templates/
├── scripts/harness/
└── tests/
```

## 검증

구조 검사를 실행합니다:

```bash
python3 scripts/harness/bootstrap.py
python3 scripts/harness/self_test.py
python3 -m unittest discover -s tests -q
```

advisory gate를 실행합니다:

```bash
python3 scripts/harness/gate.py all --tier trivial
python3 scripts/harness/gate.py all --tier normal --template
```

운영 보조 명령:

```bash
python3 scripts/harness/review_gate.py prepare --tier normal --producer main-codex
python3 scripts/harness/review_gate.py finalize --review-file harness/reviews/review-YYYYMMDDTHHMMSSZ.md
python3 scripts/harness/subagent_planner.py plan --role worker --owner worker-auth --goal "auth slice" --write-scope src/auth --claim
python3 scripts/harness/automation_planner.py scan
python3 scripts/harness/skillify_audit.py all
python3 scripts/harness/score.py --min-score 95
```

## Enforcement 모델

이 템플릿은 `advisory` mode로 시작합니다. 실제 프로젝트로 복사한 뒤에는 아래 방식으로 더 강한 enforcement로 이동할 수 있습니다.

- runtime state를 `harness/runtime.json`에 유지합니다.
- `codex_hooks = true` 설정으로 `.codex/hooks.json`을 활성화합니다.
- 완료 전에 `scripts/harness/gate.py all --tier normal`을 실행합니다.
- `review_gate.py finalize`로 self-review와 pending verdict를 차단합니다.
- `subagent_planner.py --claim`으로 write-scope 충돌을 방지합니다.
- automation intent와 proposed skill을 승격 전에 audit합니다.
- `scripts/harness/self_test.py`와 관련 gate를 실행하는 CI 또는 branch protection을 추가합니다.
- 실제 프로젝트 작업에서 최종 완료 전에 `scripts/harness/session_close.py`를 실행합니다.

Hooks는 의도적으로 optional입니다. Codex hooks는 아직 experimental surface이기 때문입니다. 신뢰할 수 있는 핵심은 결정론적 gate scripts와 review artifacts입니다.
