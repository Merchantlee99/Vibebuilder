# PRD.md — Codex Native Harness

## Problem

기존 Claude 하네스는 Codex app의 핵심 기능을 운영 구조에 직접 흡수하지 못했다. Codex에서는 subagents, worktree, automations, browser, computer use를 규칙 기반으로 잘 쓰는 것이 더 중요하다.

## Users

- Codex app를 메인 개발 환경으로 쓰는 solo builder
- 작은 팀에서 Codex를 orchestration layer로 쓰는 operator

## Key Flows

1. Operator starts a non-trivial task and grounds it in project docs.
2. Codex routes bounded questions and edits through subagents with explicit ownership.
3. Validation and review are recorded in project files.
4. Long-running work is resumed through telemetry and automations.

## Acceptance Criteria

- [x] AGENTS.md defines mode, routing, and review rules
- [x] Manifest files encode capability and mode policy
- [x] Templates support project grounding and restartability
- [x] Scripts support bootstrap, logging, review digest, mode recommendation, and audit triggers
- [ ] Validation passes via self-test and unit tests

## Risks

- v0 may be too document-heavy for very small tasks
- YAML manifests are human-friendly but not yet script-driven
- Review quality still depends on human or agent discipline

## Notes

- v0 prioritizes clear operations over maximum automation.
