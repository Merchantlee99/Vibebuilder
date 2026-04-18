---
name: qa
description: Use for UI-affecting changes before /ship. Drives an actual browser through the user flow to reproduce what the user will see — clicks, forms, error states, loading spinners. Finds the bugs that unit tests can't catch (DOM event ordering, CSS breakage, auth session edge cases, race conditions in UI state).
---

# QA

UI 변경을 실제 브라우저로 **사용자 흐름 재현** 해서 검증하는 skill.

## 언제 쓰는가

- UI 가 있는 기능 변경 (프론트엔드 코드, 템플릿, 스타일, 클라이언트 JS)
- `/ship` 직전 최종 검증
- 단위 테스트는 green 인데 "실제로 될까?" 싶은 순간
- 재현 빈도 애매한 버그 (UI race, async load, event ordering)

## 언제 쓰지 않는가

- 순수 서버 / API / CLI 변경 (→ Gate ④ 의 pytest/unit test 로 충분)
- trivial UI tweak (색상 변경 한 줄 등)
- 아직 구현 완료 안 됨 (→ `/vibe-coding-workflow` 내부 검증으로 충분)

## 도구 (솔로 환경)

gstack 은 `/browse` 전용 바이너리 (Playwright wrapper) 를 쓰지만, 이
프레임워크는 다음 중 하나를 사용:

1. **Claude-in-Chrome MCP** (`mcp__claude-in-chrome__*`) — 가장 권장.
   실제 Chrome 탭에서 DOM 조작 + 스크린샷 + network 검사 + console.
2. **Playwright** (프로젝트가 이미 쓰면) — 스크립트 기반 재현 가능
3. **수동 브라우저** — 최후. Claude 가 체크리스트를 제공하고 사용자가 클릭

## 방식

### 1. 테스트 시나리오 정의 (구현 전에도 가능)

`Plan.md` 의 acceptance criteria 를 **사용자 동작 순서** 로 번역:

```
AC-1: 사용자가 로그인 후 대시보드를 본다
→ 시나리오:
  1. Navigate /login
  2. email + password 입력
  3. submit
  4. Expect redirect /dashboard
  5. Expect user-name 요소에 "홍길동"
  6. Expect dashboard-cards >= 1 개
```

### 2. 실제 재현

Chrome MCP 쓰는 경우 단계별:
- `mcp__claude-in-chrome__navigate(url)`
- `mcp__claude-in-chrome__form_input` 로 필드 채움
- `mcp__claude-in-chrome__left_click` 로 submit
- `mcp__claude-in-chrome__get_page_text` 또는 스크린샷으로 상태 검증
- `mcp__claude-in-chrome__read_console_messages` 로 JS 에러 확인

### 3. 필수 체크

UI QA 는 다음 5가지를 **항상** 확인 (단위 테스트가 놓치는 영역):

| 영역 | 구체 체크 |
|------|----------|
| **Loading state** | spinner / skeleton 이 실제로 나타나나? |
| **Empty state** | 데이터 없을 때 무엇을 보이나? ("데이터 없음" 메시지 존재?) |
| **Error state** | 서버 5xx / 네트워크 끊김 시 UI 가 얼어붙지 않나? |
| **Auth boundary** | 로그인 없이 접근 시 redirect? 권한 없는 페이지는 403? |
| **Event ordering** | 빠르게 클릭 두 번 했을 때 중복 제출되나? |

### 4. 실패 시

- 버그 재현 영상/스크린샷 저장 (가능하면)
- Investigation skill 로 넘김 (`/investigate`)
- Ship 중단

## 출력 형식

```
# QA Run — <YYYY-MM-DD> — <feature slug>

## Scenarios tested
1. <AC-1> — PASS | FAIL
2. <AC-2> — PASS | FAIL

## 필수 체크
- Loading state: PASS / FAIL / N/A
- Empty state: PASS / FAIL / N/A
- Error state: PASS / FAIL / N/A
- Auth boundary: PASS / FAIL / N/A
- Event ordering: PASS / FAIL / N/A

## Findings
- <bug 또는 이상 동작 — 스크린샷 경로 포함>

## Console errors
- <JS error 캡처>

## Verdict
- ship-ready | fix-needed | needs-more-testing

## Attachments
- screenshots: .claude/audits/qa-<ts>/screenshot-N.png
- network traces (if captured): ...
```

저장: `.claude/audits/qa-<ts>/report.md`

## 가드레일

- "유닛 테스트 통과했으니 OK" 금지 — UI 는 DOM 에서 실제 나타나야
- 스크린샷 없는 PASS 는 약한 증거
- 실제 사용자 흐름 1개라도 빠뜨리면 FAIL 로 간주
- Console 에 에러 있으면 (보이지 않는 깨짐) ship 금지
- 모바일 viewport 도 체크 (responsive 이슈)

## 먼저 읽을 것

- `Plan.md` 의 acceptance criteria
- Implementation 의 UI 영향 파일 (components / templates / styles)
- 이전 QA 리포트 (`.claude/audits/qa-*/`) 로 회귀 유무 참조
