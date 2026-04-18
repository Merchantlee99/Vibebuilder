# Claude Harness — Unified Vibecoding Framework

**4-axis long-durability framework for solo and small-team Claude Code projects.**

이 하네스는 네 프레임워크의 장점을 하나의 계층 구조로 결합합니다:

| Layer | 원천 | 책임 |
|-------|------|------|
| **1. Workflow catalog** | [gstack](https://github.com/garrytan/gstack) | 무엇을 할지 — 20+ specialized skills |
| **2. Pipeline enforcement** | [Manta 프레임워크](https://github.com/) | 어떤 순서로 + 누가 허가 — 5-stage × role manifest |
| **3. Mechanical guardrail** | 자체 구현 (solo Claude) | 위반 시 기계 차단 — 10 gates, actor crossover, append-only |
| **4. Self-evolving loop** | [hermes-agent](https://github.com/NousResearch/hermes-agent) | 시간이 흘러도 어떻게 유지 — learning↔action feedback, skill auto-gen |

## 핵심 원칙

1. **기본 응답 언어는 한국어다.**
2. **모든 규칙은 기계가 강제한다.** 프롬프트로 "조심하세요" 하지 않는다. 위반 시 `exit 2`.
3. **AI 혼자 자기 작업을 승인할 수 없다.** actor crossover 불변식 (Gate P2-F).
4. **append-only 감사 로그.** events.jsonl / learnings.jsonl 은 절대 rewrite 안 한다.
5. **프레임워크는 쓸수록 스스로 적응한다.** Layer 4가 learnings → 다음 행동 자동 반영.
6. **자가진화는 제안만, 적용은 사용자 승인.** 기계가 규칙을 혼자 느슨하게 못 한다.
7. **장기 작업의 기억은 채팅이 아니라 파일에.** 6개 필수 산출물 (Prompt/PRD/Plan/Implement/Documentation/Subagent-Manifest).

## 디렉토리 레이아웃

```
<project>/
├── CLAUDE.md                    # Claude 측 운영 헌법
├── AGENTS.md                    # secondary reviewer (user / claude-reviewer) 측 규약
├── ETHOS.md                     # 장기 철학 (무너지지 않는 원칙)
├── README.md                    # 이 문서
├── .claude/
│   ├── settings.local.json      # Claude Code 훅 등록
│   ├── hooks/                   # Layer 2+3 Python 훅
│   │   ├── session_start.py
│   │   ├── user_prompt_submit.py
│   │   ├── pre_tool_use.py
│   │   ├── post_tool_use.py
│   │   └── stop.py
│   ├── skills/
│   │   ├── _manual/             # 사람이 쓴 정적 skills (gstack/Manta 스타일)
│   │   └── _evolving/           # Layer 4 자동 생성 skills
│   ├── agents/
│   │   ├── manifest.json        # 역할 정의 + writes/reads allowlist
│   │   └── review-matrix.json   # 5-stage pipeline
│   ├── sealed-prompts/          # 고정 red-team 프롬프트
│   ├── memory/
│   │   ├── project-profile.md   # dialectic user model (hermes 식)
│   │   └── session-index.sql    # FTS5 검색 스키마
│   ├── reviews/                 # Gate ② 산출물 (리뷰 파일)
│   ├── direction-checks/        # Gate ① 산출물 (방향검증)
│   ├── spikes/                  # Gate ⑩ 산출물 (병렬 설계 스파이크)
│   ├── audits/                  # meta-audit + insights + taxonomy 제안
│   ├── events.jsonl             # append-only 감사 로그
│   ├── learnings.jsonl          # append-only 학습 로그
│   ├── runtime.json             # 프레임워크 상태 + gates 플래그
│   └── known-gaps.md            # 의도적 미흡 + trace-gathering 기준
├── scripts/harness/
│   ├── event_log.py             # Layer 3 core
│   ├── learning_log.py
│   ├── size_check.py            # tier + complexity 분류
│   ├── bash_write_probe.py      # Bash 우회 탐지
│   ├── rotate_logs.py           # segmented append-only 회전
│   ├── self_test.py             # 10 gates + 역할 + skills 헬스체크
│   ├── meta_supervisor.py       # 자동 meta-audit trigger
│   ├── oversight_policy.py      # Layer 2 (Manta 포팅)
│   ├── risk_policy.py
│   ├── review_matrix_policy.py
│   ├── transition_policy.py
│   ├── runtime_gate.py
│   ├── memory_manager.py        # Layer 4 pre/post turn 학습 hook
│   ├── skill_auto_gen.py        # 자동 skill 초안 제안
│   ├── taxonomy_learner.py      # FAILURE_TAXONOMY 자가 성장 제안
│   ├── insights_engine.py       # 주간/월간 사용 패턴 분석
│   └── session_index.py         # FTS5 과거 대화 검색
├── templates/                   # Manta 필수 산출물 템플릿
│   ├── Prompt.md
│   ├── PRD.md
│   ├── Plan.md
│   ├── Implement.md
│   ├── Documentation.md
│   └── Subagent-Manifest.md
└── tests/
    └── test_harness.py          # 단위 테스트
```

## 10개 기계 차단 gates (Layer 3)

| # | 이름 | 트리거 | 작동 |
|---|------|--------|------|
| ① | 방향 확인 | 대규모 변경 전 | user (또는 isolated claude-reviewer) 가 방향 승인 |
| ② | 상호 리뷰 | 구현 완료 시 | **actor crossover 강제** + fingerprint + rollback 체크 + 최근 Gate ④ pass 요구 |
| ③ | 학습 기록 | 실수 감지 시 | 자동으로 learnings.jsonl 에 패턴 기록 |
| ④ | 테스트 실행 | 코드 변경 시 | 결정론적 도구 (ruff/mypy/pytest), per-file latest |
| ⑤ | 맥락 로드 | 세션 시작 시 | 최근 learnings + 블록 + session id를 snapshot 에 |
| ⑥ | 스코프 체크 | 변경 누적 시 | tier×complexity + Bash 우회 탐지 |
| ⑦ | 자기 보호 | 훅/정책 파일 수정 시도 | control-plane 차단 (산출물 경로는 허용) |
| ⑧ | 주장 검증 | 마크다운/코드/Bash 에 보호경로 허위 주장 시 | advisory flag |
| ⑨ | 신뢰 경계 | 외부 데이터 응답 에 prompt-injection 패턴 | advisory flag |
| ⑩ | 병렬 스파이크 | high-risk + complex + 사용자 opt-in | 두 설계안 병렬 작성 + 비교 |

## 5-stage pipeline (Layer 2)

```
plan → tests → implementation → verification → postmortem
```

각 단계마다 `required_reviewers` 로 지정된 역할이 pass 기록 후 다음 단계 진입 가능 (`.claude/agents/review-matrix.json`).

> **Note on dispatch.** 이 프레임워크는 reviewer 를 **자동 호출하지 않는다**. Post-hook 은 `review-needed` 이벤트를 `events.jsonl` 에 기록만 하고, 실제 리뷰는 **user (또는 별도 isolated Claude 세션)** 이 `.claude/reviews/<ts>.md` 를 작성하고 `python3 scripts/harness/event_log.py 02 pass <actor> ...` 로 확정해야 다음 편집이 열린다. Gate ② P2-F 는 author actor 와 reviewer actor 가 다른지만 기계적으로 검증한다 — 누가 리뷰할지는 결정하지 않는다.

## Enforcement modes

런타임 상태 (`.claude/runtime.json → mode`) 는 명시적 3단계:

| mode | 동작 | 언제 사용 |
|------|------|----------|
| `bootstrap` | Gate ⑦ hard block + 나머지 게이트는 `advisory` (이벤트만 기록, 차단 없음). `allow_dirty_worktree: true` | 신규 프로젝트 첫 며칠. 기존 코드베이스에 하네스 이식 중 |
| `advisory` | 모든 게이트가 이벤트를 기록하지만 `exit 2` 는 Gate ⑦ / ⑥ (high-risk 초과) 만. `bash_write_probe`, Gate ⑧/⑨ 는 여전히 advisory | baseline 수집 완료 후, 팀이 flow 에 익숙해지는 단계 |
| `enforced` | 모든 게이트가 위반 시 `exit 2`. `allow_dirty_worktree: false`, Gate ④ 실패 시 후속 edit 차단 | 실제 운영 모드. `bootstrap.enforcement_phase` 를 수동 promote 할 때 진입 |

전환 기준은 `.claude/runtime.json → bootstrap.full_mode_requirements` 에 나열된 3개 조건이 모두 만족될 때 user 가 수동 변경:
1. dirty worktree baseline refresh 또는 제거
2. 변경된 surface 에 대해 결정론적 게이트 (ruff/mypy/pytest) 가 green
3. commit/push 게이트를 advisory → blocking 으로 전환

**현재 디폴트는 `bootstrap` 이다.** 공유 템플릿으로 배포 시 README 의 "기계적 강제" 언어는 `enforced` mode 기준임을 유의.

## 필수 산출물 (Layer 2, Manta 식)

비사소한 작업은 다음 6개 파일 기준으로 진행:

| 파일 | 목적 |
|------|------|
| `Prompt.md` | 목표, 비목표, 제약, done-when |
| `PRD.md` | 사용자 문제, 핵심 흐름, acceptance criteria, 리스크 |
| `Plan.md` | milestone, 검증 계획, 순서, 종료 조건 |
| `Implement.md` | 현재 작업 범위, write paths, 검증 루프 |
| `Documentation.md` | 상태, 결정 로그, known issues, 재개 지점 |
| `Subagent-Manifest.md` | 역할, 호출 시점, write scope, 종료 기준 (선택) |

## Self-evolving 폐곡선 (Layer 4)

```
매 턴 pre-hook:  learnings.jsonl → 관련 top-5 prefetch → 프롬프트 주입
매 턴 post-hook: 이번 턴 block/failure → learnings.jsonl 갱신
                 성공 패턴 ≥ 3건 축적 시 → _evolving/ skill 초안 제안
주기 meta-audit: 패턴 분석 → sealed-prompt 재검토 제안
                 tier 임계값 자동 튜닝 제안
                 FAILURE_TAXONOMY 에 unknown 3+ 건 clustering 후 후보 제안
적용은 항상 사용자 승인 경로로.
```

## 설치

### 새 프로젝트 시작 시

```bash
# 1. 템플릿 클론 (또는 레포 복사)
git clone <this-repo> /your/project && cd /your/project

# 2. 부트스트랩 — 설정 생성, 권한 부여, 빈 로그 초기화, self-test 실행
python3 scripts/harness/bootstrap.py

# 3. (이 레포에서 복사 배포한 경우) 이전 이력 제거
python3 scripts/harness/bootstrap.py --reset-logs

# 4. 필수 산출물 템플릿 복사 (최초 한 번)
cp templates/{Prompt,PRD,Plan,Implement,Documentation,Subagent-Manifest}.md ./
```

`bootstrap.py` 는 멱등. 기존 설정을 덮어쓰려면 `--force`. 출력 마지막에 `bootstrap OK — harness is live.` 가 나와야 설치 성공.

### 모드 승격

기본 모드는 `bootstrap` (advisory). 실사용 진입 시:

```bash
python3 scripts/harness/bootstrap.py --promote advisory   # (bootstrap 이후)
python3 scripts/harness/bootstrap.py --promote enforced   # pre-flight 후
```

`enforced` 승격 전 pre-flight: (a) 깨끗한 git worktree, (b) self_test green, (c) 유닛 테스트 green. 하나라도 실패 시 차단.

### 기존 프로젝트에 이주 시

아직 자동 migration 스크립트 없음. 수동 이주:
1. `.claude/`, `scripts/harness/`, `templates/` 세 디렉토리를 복사
2. 기존 훅이 있으면 `.bak` 로 이동한 뒤 이 프레임워크 훅으로 교체
3. 첫 세션에서 meta-audit 가 기존 프로젝트의 파일 분포 학습 → 며칠 뒤 tier 임계값 제안

## First-run checklist

복제 직후 다음 명령으로 프레임워크가 제대로 설치됐는지 확인:

```bash
# 1. 헬스체크 — 5 hooks + 18 scripts + 4 docs + 5 core + 13 sealed
python3 scripts/harness/self_test.py

# 2. 단위 테스트
python3 -m unittest discover -s tests -q

# 3. SessionStart 훅 smoke
echo '{"hook_event_name":"SessionStart","cwd":"'"$PWD"'"}' | python3 .claude/hooks/session_start.py
```

**예상 결과**:
- self_test: `Harness is live.`
- unit tests: `OK` (현재 57 tests — 수는 추가에 따라 증가)
- session_start: exit 0, `.claude/context-snapshot.md` 생성

하나라도 실패하면 설치 문제. `python3 scripts/harness/bootstrap.py --force` 로 재부트스트랩.

### 첫 실전 편집

trivial tier (≤ 20 LOC 1 file) 는 바로 편집 가능. normal 이상은 다음 순서:

1. `Prompt.md` → `PRD.md` → `Plan.md` 작성 (→ tier 선언)
2. Secondary reviewer 에게 `direction-check.md` 로 invoke → `.claude/direction-checks/<ts>.md`
3. `python3 scripts/harness/event_log.py 01 pass <reviewer> <target> <<JSON {...} JSON` 로 기록
4. 실제 편집 시도 → Gate ① 통과, Post 에서 review-needed 자동 기록
5. Secondary reviewer 에게 `review-code.md` invoke → `.claude/reviews/<ts>.md`
6. `02 pass <reviewer-actor>` 기록 → 다음 편집 허용
7. 전 단계 pass 이벤트의 actor 는 **반드시 author 와 다름** — Gate ② P2-F 가 기계 차단

## 현재 상태 (2026-04-18, 솔로 프레임워크 v1.2)

- **구조**: 5 hooks + 19 scripts + 13 sealed + 6 templates + 4 skills + 4 docs
- **문서**: 솔로 모델 (author=claude, reviewer=user, Codex 미사용)
- **Layer 3 enforcement**: 구현 완료 + **circuit breaker fail-closed on tripped**
- **Layer 2 pipeline**: manifest v2.1-solo, reviewer dispatch = manual
- **Layer 4 self-evolving**: 핵심 구현 + memory prefetch → user_prompt_submit
- **Tests**: 57/57 unit + rotate stress PASS. 행동 테스트 포함 (Gate ⑦ 실제 block, circuit severity 3-state, env bypass 회귀)
- **설치**: `bootstrap.py` 단일 진입점. `--reset-logs` / `--promote` 서브커맨드

### Skills 카탈로그 (8개)

작업 단계별로 순차 사용. 솔로 환경 기준.

| 단계 | Skill | 역할 |
|------|-------|------|
| 문제 정의 | `/office-hours` | 아이디어 reframe, go/no-go |
| 기획 잠금 | `/product-planner` | readiness 3-lens 판정 |
| 설계 잠금 | `/plan-eng-review` | architecture / data flow / edge / tests 검토 |
| 구현 | `/vibe-coding-workflow` | milestone slice + scope freeze + doc sync |
| 디버깅 | `/investigate` | proximate / root / systemic 원인 분리 |
| 검증 | `/review` | pre-landing 코드 리뷰 (Gate ②) |
| UI 검증 | `/qa` | 실제 브라우저로 사용자 플로우 재현 |
| 배포 | `/ship` | 문서 sync + 테스트 green + PR open |

자동 생성 영역 (`_evolving/`) 은 3건 이상 패턴 축적 시 skill 초안이 자동 제안됨. 사용자 승인 시 `_manual/` 로 이관.

### 솔로 사용 시 actor 규약

| Actor | 언제 | 역할 |
|-------|------|------|
| `claude` | 이 Claude Code 세션에서 편집 중 | author — 설계/분석/구현 초안 |
| `user` | 사용자 본인이 diff/plan 읽고 판단 후 `02 pass` 기록 | 기본 reviewer |
| `claude-reviewer` | 별도 Claude Code 세션 (context 격리, sealed prompt 만 읽음) | 선택적 보조 reviewer |
| `system` | 자동 도구 (hooks, runners) | 비actor (기계) |

Gate ② P2-F 불변식: `claude == claude` 자기 리뷰는 기계 차단. `claude → user` 또는 `claude → claude-reviewer` 교차 필수.

## 언어와 스타일

- 기본 응답: **한국어**
- 커밋 메시지: conventional commit prefix (`feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `chore:`)
- 문서: 명령형 (`~할 것`) 이 아니라 평서형 (`~는 ~다`)

## 라이선스

MIT
