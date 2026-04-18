# AGENTS.md — Secondary Reviewer 규약 (축소본)

## 이 문서의 위상 (솔로 프레임워크)

**현재 이 프레임워크는 솔로 Claude 개발자용이며, Codex 등 외부 AI 리뷰어는 사용하지 않는다.**

Secondary reviewer 역할은 다음 중 하나가 수행한다:

| 주체 | actor 값 | 언제 |
|------|---------|------|
| **사용자(본인)** | `user` | 기본 경로. 모든 Gate ②/① 리뷰 |
| **Isolated Claude session** | `claude-reviewer` | 선택. 별도 세션에서 context 격리한 뒤 sealed-prompt 만 보고 리뷰 |

상세 규약은 **CLAUDE.md** 에 통합되어 있다. 이 문서는 참조용 요약이다.

## Isolated Claude session 을 쓰는 경우

사용자가 직접 리뷰하기엔 시간 부족 + high-risk 하지 않은 변경일 때, 별도 Claude Code 세션을 열어 다음처럼 사용:

1. 새 Claude Code 세션 시작 (다른 IDE 창 또는 CLI 인스턴스)
2. 해당 세션에 이 레포를 읽기 전용 맥락으로만 제공
3. 세션에게 `.claude/sealed-prompts/review-code.md` (또는 `review-plan.md`) 만 읽고 리뷰하도록 지시
4. 세션이 `.claude/reviews/<ts>.md` 작성 후 `actor=claude-reviewer` 로 기록

**주의**: 같은 모델이라 correlated blindness 가능. 고위험 변경은 무조건 user 본인 리뷰.

## 금지 사항 (솔로 환경에서도 유지)

- 테스트 스킵 / pass 스텁 / mock.patch 자기 자신 — Gate ④ 에서 탐지
- 멀티 컨선 커밋 (refactor + fix + feature)
- diff 에 주석 처리된 코드 남기기
- 새 TODO / FIXME 추가 (기존 수정은 OK)
- 시크릿 노출 → 즉시 `<SECRET_DETECTED>`

## Claude 반환 형식 (구조화)

```
Status: success | failure | blocked | scope_drift | repeated_failure
Files: <list>
Commands: <literal + exit>
Findings: <if review task>
Next: <user action expected>
```

## 한 줄 요약

```
이 프레임워크의 "reviewer" = 사용자 (또는 선택적 isolated Claude session).
Codex 경로 없음. 자세한 규약은 CLAUDE.md 참조.
```
