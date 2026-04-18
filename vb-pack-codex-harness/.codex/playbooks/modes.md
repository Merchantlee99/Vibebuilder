# Modes Playbook

## Local

기본 orchestration 모드다. 계획, 문서, git 상태 확인, 작은 수정, 비밀정보가 필요한 작업에 쓴다.

## Worktree

비사소한 구현의 기본값이다. 특히 worker subagent가 코드를 쓰면 우선 고려한다.

### Move to Worktree When

- 여러 파일을 건드린다
- refactor다
- merge conflict 가능성이 있다
- reviewer와 author 흐름을 분리하고 싶다

## Cloud

깨끗한 환경에서 읽거나 재현해보는 검증 모드다.

### Use Carefully

- 로컬 시크릿에 기대면 안 된다
- 환경 의존 write 작업에는 기본값이 아니다
