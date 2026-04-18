---
name: ship
description: Final pre-release gate. Ensures tests green, docs synced, changelog updated, then pushes and opens PR. One command for the "I'm done, let's ship it" moment.
---

# Ship

구현 + review + verification 이 모두 끝난 뒤 **실제 착륙** 시키는 skill.

## 언제 쓰는가

runtime.json gates 가 **모두** true:

- `scope_locked == true`
- `plan_reviewed == true`
- `failing_tests_committed == true`
- `implementation_verified == true`
- `deterministic_verified == true`

하나라도 false 면 이 skill 은 **stop** 하고 누락된 게이트를 알려준다.

## 언제 쓰지 않는가

- 위 전제 조건 충족 전
- 릴리스 대상이 아닌 WIP 커밋

## 방식

### 1. Pre-ship 체크

```bash
python3 -c "
import json
rt = json.load(open('.claude/runtime.json'))
gates = rt['gates']
missing = [k for k,v in gates.items() if k != 'ship_approved' and not v]
if missing:
    print('MISSING:', missing)
    import sys; sys.exit(1)
print('all gates green')
"
```

미통과 게이트가 있으면 해당 sealed prompt 로 돌아가서 마무리.

### 2. 문서 동기화

- `Documentation.md` → 이번 변경 반영됐나?
- `Implement.md` → 완료된 slice 는 Documentation 의 Changelog 로 이관?
- `README.md` → 외부 인터페이스 변경 시 업데이트?

### 3. 최종 run

- `bun test` / `pytest -q` / 프로젝트 기본 test 명령
- 실패하면 ship 중단

### 4. 커밋 + 푸시

- `git status` 깨끗한지 확인
- 커밋 메시지 형식: `<type>(<scope>): <≤60자 요약>`
- 한 PR = 한 logical change (M1 slice 여러 개면 squash 검토)

```bash
git push -u origin <branch>
```

### 5. PR 생성

```bash
gh pr create --title "<title>" --body "$(cat <<'EOF'
## Summary
- <bullet>

## Plan reference
- <link to Plan.md section>

## Test plan
- [x] <test command>
- [x] <e2e scenario>

## Rollback plan
<from Plan.md>

🤖 Generated via /ship skill
EOF
)"
```

### 6. `ship_approved` flip

```bash
python3 scripts/harness/runtime_gate.py approve-ship
```

이후 주기 meta-audit 에서 ship 후 24시간 내 hotfix 가 있는지 모니터링.

## 출력 형식

```
Ship check:
- gates green: yes/no
- docs synced: yes/no
- tests green: yes/no

PR: <URL>
Next: <if any post-ship actions required>
```

## 가드레일

- `--no-verify`, `--no-gpg-sign` 금지 (사용자 명시 승인 없이)
- 이미 로컬 밖으로 나간 커밋 amend 금지
- force push to main/master 금지
- `deterministic_verified == true` 없이 ship 금지 (Gate ④ 우회 방지)
- `ship_approved` flip 은 **마지막에** (rollback 쉽게 하기 위해)

## 먼저 읽을 것

- `runtime.json` (gate 플래그 상태)
- `Documentation.md` (changelog 대기 항목)
- `Plan.md` (원래 scope 와 일치 확인)
- 최근 `.claude/reviews/*.md` (review verdict)
