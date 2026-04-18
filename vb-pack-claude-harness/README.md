# Claude Harness — Unified Vibecoding Framework

**4-axis long-durability framework for solo and small-team Claude Code projects.**

이 하네스는 네 프레임워크의 장점을 하나의 계층 구조로 결합합니다:

| Layer | 원천 | 책임 |
|-------|------|------|
| **1. Workflow catalog** | [gstack](https://github.com/garrytan/gstack) | 무엇을 할지 — 20+ specialized skills |
| **2. Pipeline enforcement** | [Manta 프레임워크](https://github.com/) | 어떤 순서로 + 누가 허가 — 5-stage × role manifest |
| **3. Mechanical guardrail** | v3 (Claude↔Codex harness) | 위반 시 기계 차단 — 10 gates, actor crossover, append-only |
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
├── AGENTS.md                    # Codex / secondary reviewer 측 규약
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
| ① | 방향 확인 | 대규모 변경 전 | Codex / secondary reviewer가 방향 승인 |
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
# 1. 템플릿 복사
cp -r /path/to/01_claude_harness/.claude /your/project/
cp -r /path/to/01_claude_harness/scripts /your/project/
cp -r /path/to/01_claude_harness/templates /your/project/
cp /path/to/01_claude_harness/{CLAUDE,AGENTS,ETHOS,README}.md /your/project/

# 2. 실행 권한
chmod +x /your/project/.claude/hooks/*.py
chmod +x /your/project/scripts/harness/*.py

# 3. 필수 산출물 초기화
cp /your/project/templates/{Prompt,PRD,Plan,Implement,Documentation,Subagent-Manifest}.md \
   /your/project/

# 4. 프레임워크 상태 초기화
cp /your/project/templates/runtime.initial.json /your/project/.claude/runtime.json

# 5. 헬스체크
python3 /your/project/scripts/harness/self_test.py
```

모든 10 gates 가 `active`, scripts 가 `ok` 로 표시돼야 설치 성공.

### 기존 프로젝트에 이주 시

아직 자동 migration 스크립트 없음. 수동 이주:
1. `.claude/`, `scripts/harness/`, `templates/` 세 디렉토리를 복사
2. 기존 훅이 있으면 `.bak` 로 이동한 뒤 이 프레임워크 훅으로 교체
3. 첫 세션에서 meta-audit 가 기존 프로젝트의 파일 분포 학습 → 며칠 뒤 tier 임계값 제안

## First-run checklist

복제 직후 다음 명령으로 프레임워크가 제대로 설치됐는지 확인:

```bash
# 1. 실행 권한
chmod +x .claude/hooks/*.py scripts/harness/*.py

# 2. 헬스체크 — 5 hooks + 17 scripts + 4 docs + 5 core + 13 sealed
python3 scripts/harness/self_test.py

# 3. 단위 테스트 — 40 tests
python3 -m unittest discover -s tests -v

# 4. SessionStart 훅 smoke
echo '{"hook_event_name":"SessionStart","cwd":"'"$PWD"'"}' | python3 .claude/hooks/session_start.py
```

**예상 결과**:
- self_test: `Harness is live.`
- unit tests: `Ran 40 tests ... OK`
- session_start: exit 0, `.claude/context-snapshot.md` 생성

하나라도 실패하면 설치 문제. README 설치 섹션 재확인 또는 이슈 제기.

### 첫 실전 편집

trivial tier (≤ 20 LOC 1 file) 는 바로 편집 가능. normal 이상은 다음 순서:

1. `Prompt.md` → `PRD.md` → `Plan.md` 작성 (→ tier 선언)
2. Secondary reviewer 에게 `direction-check.md` 로 invoke → `.claude/direction-checks/<ts>.md`
3. `python3 scripts/harness/event_log.py 01 pass <reviewer> <target> <<JSON {...} JSON` 로 기록
4. 실제 편집 시도 → Gate ① 통과, Post 에서 review-needed 자동 기록
5. Secondary reviewer 에게 `review-code.md` invoke → `.claude/reviews/<ts>.md`
6. `02 pass <reviewer-actor>` 기록 → 다음 편집 허용
7. 전 단계 pass 이벤트의 actor 는 **반드시 author 와 다름** — Gate ② P2-F 가 기계 차단

## 현재 상태 (2026-04-18, 솔로 프레임워크 v1.1)

- **구조**: 100% 완결 (5 hooks + 18 scripts + 13 sealed + 6 templates + 4 skills + 4 docs)
- **문서**: 솔로 모델로 재작성됨 (author=claude, reviewer=user, Codex 미사용)
- **Layer 3 enforcement**: 100% 구현 + **circuit breaker** (3연속 실패 시 자동 disable)
- **Layer 2 pipeline**: 100% 구현, manifest.json v2.0-solo
- **Layer 4 self-evolving**: 핵심 구현 완료 + memory prefetch → user_prompt_submit 통합
- **Tests**: 40/40 unit + E2E 솔로 6/6 PASS + rotate 5MB 스트레스 PASS

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
