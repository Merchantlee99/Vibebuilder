---
name: review
description: Pre-landing code review. Finds bugs that pass CI but break in prod. Runs after implementation and before ship. Maps to Gate ② (mutual review) for code artifacts.
---

# Review

구현이 끝난 diff 를 **착륙 전 최종 검토** 하는 skill. Gate ② 의 실제
운영자.

## 언제 쓰는가

- `runtime.json → gates.implementation_verified == true`
- PR 이 준비됐고 `ship` 전 마지막 점검
- tier 가 normal 이상

## 언제 쓰지 않는가

- trivial tier 변경 (직접 merge)
- 아직 구현 중 (`Implement.md` 의 validation loop 가 먼저)

## 방식

`.claude/sealed-prompts/review-code.md` 를 따른다. 아래는 운영 가이드.

### 1. 누가 review 하는가

- 작성자 actor 가 `claude` 면 reviewer 는 `user` 또는 isolated `claude-reviewer` 세션
- 이 프레임워크는 Codex 경로를 사용하지 않는다 (CLAUDE.md / AGENTS.md 참조)
- Gate ② P2-F 는 같은 actor 가 self-review 를 기록하는 것을 기계 차단

### 2. 무엇을 읽는가

- diff 전체
- 영향받은 파일 주변 20줄
- 이 변경이 import/call 하는 파일
- 최근 `.claude/test-runs/run-*.log`
- `.claude/learnings.jsonl` 마지막 20줄

### 3. Rollback triggers 체크 (필수)

review-code.md 의 7가지 항목을 **explicit** 하게 확인:

1. Public API signature 변경 → migration path?
2. Test 수 감소 / skip / xfail?
3. Performance 경로 regression?
4. Security 경로 변경 + 대응 test?
5. 새 TODO/FIXME?
6. Commented-out code?
7. One-way schema migration?

### 4. Test oracle 무결성

구현 + 테스트가 **같은 커밋** 에서 바뀌면 red flag. reviewer 는:

- Fail-before 증거 요구 (기존 test 가 이 버그 잡았는지)
- Pass-after 증거 요구
- 없으면 기본 verdict = `revise`

### 5. Verdict 기록

```bash
python3 scripts/harness/event_log.py 02 pass <reviewer-actor> <reviewed-file> <<JSON
{
  "reviewer_file": ".claude/reviews/<ts>.md",
  "summary": "<verdict + top finding>",
  "reviewed_file": "<path>",
  "verdict": "accept|revise|reject"
}
JSON
```

## 출력 형식

`review-code.md` sealed prompt 형식 그대로 `.claude/reviews/<ts>.md` 에
작성. 주요 섹션:

- Verdict (accept / revise / reject [Rollback recommended: ...])
- Severity of worst finding
- Objections (ranked, worst first) — 최소 2개 (normal) / 3개 (high-risk)
- Tests actually exercising this change
- Assumptions made to review
- Rollback triggers (fired or none)

## 가드레일

- "LGTM" 금지
- Objection 수 요건 미만이면 `<INSUFFICIENT_OBJECTIONS>` 로 stop
- Rollback triggers 체크 섹션 누락 시 Gate ② Pre 가 다음 편집을 차단
- Reviewer_file 이 800B 미만이거나 구조화된 Objection block 이 없으면 자동 거부 (Gate ② 내부 검증)

## 먼저 읽을 것

- `.claude/sealed-prompts/review-code.md`
- 대상 diff (`git diff`)
- `Plan.md` (원래 scope 와 일치하는지)
