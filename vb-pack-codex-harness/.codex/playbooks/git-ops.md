# Git Ops Playbook

## Order of Operations

1. built-in git로 status, diff, log 확인
2. 추가 정보가 필요하면 터미널 사용
3. 검증 후 commit scope를 하나의 논리 변경으로 유지

## Default Checks

- `git status --short`
- `git diff --stat`
- `git diff`
- relevant tests

## Red Flags

- unrelated changes mixed into one commit
- rollback path 없음
- docs와 code가 같이 안 움직임
