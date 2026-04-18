# Known Gaps — Unified 4-axis Harness

의도적으로 미흡한 부분 + 각 항목을 개선할 trace-gathering 기준.

## Scope

이 문서는 **프레임워크 자체가 아직 다루지 않는 실패 경로** 를 명시한다. 해당 경로가 실제로 자주 발생하는지 events.jsonl 에 누적되는 패턴을 기준으로 확장 여부를 판단한다.

## Layer 3 (Mechanical guardrail) 의 known gap

| ID | 경로 | 왜 안 잡는지 | 확장 기준 |
|----|------|-------------|-----------|
| L3-G1 | Agent subagent `prompt=` 필드의 허위 주장 | Edit/Write 가 아니라 Gate ⑧ 가 안 봄 | 동일 패턴 3건 이상 `pattern_validated=false` |
| L3-G2 | Bash heredoc 으로 non-markdown 파일에 기록 | tee / sed / printf / install 외 패턴 | 신규 Bash 쓰기 패턴 3건 이상 |
| L3-G3 | events.jsonl `detail.summary` / `detail.reason` 본문 | 스캐너가 detail 본문 안 읽음 | summary 에 허위 주장 3건 |
| L3-G4 | Git commit 메시지 / PR 설명 | Edit/Write surface 바깥 | 3건 커밋에서 protected-path 허위 |
| L3-G5 | 훅 circuit breaker 미구현 | 3연속 실패 훅 자동 disable 로직 아직 | 훅 실패 10건 이상 + timeout 복구 경로 검증 |

## Layer 4 (Self-evolving) 의 known gap

| ID | 경로 | 왜 안 잡는지 | 확장 기준 |
|----|------|-------------|-----------|
| L4-G1 | Agent-curated memory 의 악용 탐지 | 현재 Claude 가 memory 에 스스로 편의 패턴 기록 가능 | Memory provenance 로그 추가 검토 |
| L4-G2 | Skill auto-gen 의 잘못된 제안 루프 | 3건 패턴이 drift 방향이면? | 사용자 rejection 률 모니터링 |
| L4-G3 | Insights engine 의 tier 임계값 제안 검증 | 과적합된 제안 가능성 | 실제 적용 후 regressions 추적 |
| L4-G4 | Taxonomy self-growth 의 중복 패턴 | frozenset 이라 유사 vocabulary 중복 | similarity clustering 추가 |

## Layer 2 (Pipeline) 의 known gap

| ID | 경로 | 왜 안 잡는지 | 확장 기준 |
|----|------|-------------|-----------|
| L2-G1 | Role writes/reads allowlist 자동 학습 | 현재 manifest.json 정적 정의 | 3건 이상 allowlist 부족 이벤트 |
| L2-G2 | Stage 전환 강제 (plan → tests → impl) | advisory phase 에서 soft | full phase 로 전환 후 강제 |
| L2-G3 | required_reviewers 병렬 처리 | 현재 순차만 | 병렬 처리 필요성 실증 후 |

## Layer 1 (Workflow) 의 known gap

| ID | 경로 | 왜 안 잡는지 | 확장 기준 |
|----|------|-------------|-----------|
| L1-G1 | SKILL.md 자동 갱신 | `.tmpl` 기반 gen 스크립트 아직 | 수동 갱신 불편함 3건 |
| L1-G2 | 다른 언어 / 프레임워크 워크플로 | 현재 gstack + Manta skills 10개 내외 | 특정 도메인 (DevOps, ML, Data) 확장 요청 |

## 재검토 주기

- 매 분기: `meta_supervisor.py` 가 events.jsonl 에서 각 gap 의 발생 횟수 측정
- 기준 충족 시 `.claude/audits/gap-promotion-proposal-<ts>.md` 에 제안 자동 작성
- 사용자 승인 후 해당 gap 을 Layer 3/4 에 편입

## 변경 이력

- 2026-04-18: initial list. 10 gates + self-evolving 기준으로 식별된 gap 18개 기록.
- 2026-04-18: **P0-P3 완료** — Gate ② Pre 실구현 (actor crossover + fingerprint
  + rollback + per-file Gate ④), Gate ④ detached runner 추가, Layer 4 의
  `skill_auto_gen.scan_for_patterns()` + `memory_manager.sync_turn()` 실구현,
  E2E live test 6/6 PASS. 40/40 unit test green.
- 2026-04-18: **Skills 확장** — 8개 `_manual/` skill 구성:
  office-hours / product-planner / plan-eng-review / vibe-coding-workflow /
  investigate / review / qa / ship. gstack + Manta 베스트 조합으로
  솔로 Claude 워크플로 전 단계 커버.
- 2026-04-18: **솔로 프레임워크 전환 (T1-T2 완료)**:
  - 13 sealed-prompts "opposite AI" → "fresh-eye reviewer (user / isolated
    Claude session)" 교정
  - CLAUDE.md 솔로 모델 재작성 (author=claude, reviewer=user 불변식)
  - AGENTS.md 축소 (secondary reviewer = user, Codex 경로 제거)
  - manifest.json v2.0-solo: 모든 role 의 `performed_by` 명시
  - 훅 circuit breaker (`hook_health.py`) + 5개 훅 모두 통합 — 3연속 실패 시 자동 disable
  - E2E 솔로 actor 조합 6/6 PASS (claude→user 교차 + claude-reviewer 교차 + self-review 차단)
  - rotate_logs 5MB 스모크 통과 (60,100 events 무결 복원)
  - memory_manager.prefetch_context → user_prompt_submit 훅 통합 확인

## 검증 상태 (2026-04-18 기준)

| 항목 | 결과 |
|------|------|
| `self_test.py` | ✅ 5 hooks + 18 scripts + 4 docs + 5 core + 13 sealed verified |
| Unit tests (`tests/test_harness.py`) | ✅ 40/40 PASS |
| E2E Gate ② live (solo: claude→user + self-review block + claude-reviewer release) | ✅ 6/6 PASS |
| rotate_logs 5MB 스트레스 | ✅ 60,100 events intact after rotation + live append |
| Circuit breaker wiring | ✅ 5/5 hooks 통합 (hook_health.py) |
| memory_manager prefetch | ✅ user_prompt_submit 에서 top-5 learnings 주입 확인 |
| 모든 Python 파일 AST parse | ✅ OK |
| 모든 훅 파일 executable | ✅ OK |

## 첫 실전 사용 시 해야 할 것

1. 프로젝트 루트에 복제 (README 설치 섹션)
2. `templates/` 의 6개 필수 산출물 복사 + 프로젝트 목표로 채움
3. `python3 scripts/harness/self_test.py` — 전체 green 확인
4. `python3 -m unittest discover -s tests -v` — 40 tests PASS 확인
5. 첫 non-trivial 편집 시도 → Gate ① block 확인 (정상)
6. Direction-check 기록 후 → 편집 진행
7. 편집 후 → review-needed 자동 기록 확인
8. Secondary reviewer (codex 또는 user) invoke → `.claude/reviews/<ts>.md` 작성
9. `02 pass <reviewer-actor>` 기록 → 다음 편집 허용
10. 2주 사용 후 `scripts/harness/insights_engine.py --force` 로 첫 rollup

