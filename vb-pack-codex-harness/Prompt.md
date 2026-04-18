# Prompt.md — Codex Native Harness

## Goal

Build a Codex-only vibecoding harness that uses Codex app capabilities as first-class operating primitives.

## Non-Goals

- Reproducing the Claude hook system as-is
- Supporting non-Codex primary agents
- Building a full plugin ecosystem in v0

## Constraints

- Codex app 단독 사용을 전제로 한다.
- 장기 대형 프로젝트에서 안정적으로 운용 가능해야 한다.
- Python scripts should stay stdlib-only where possible.

## Done-When

- [x] Core governance docs exist
- [x] `.codex` manifests and playbooks exist
- [x] templates and baseline scripts exist
- [x] validation logs are fully green

## Open Questions

- Should later versions add automated worktree creation helpers?
