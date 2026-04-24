# Decisions

## D-001: Keep `.codex` Static

Runtime state, telemetry, reviews, and audits live under `harness/` to avoid mixing mutable project state with Codex control-plane configuration.

## D-002: Natural Language First

Users do not need to call harness commands manually during normal work. Codex should use skills and gates when the task warrants them.

## D-003: Review Independence

`normal` and `high-risk` work requires independent review. Producers do not approve their own output.

## D-004: Hooks Are Optional

Hooks are prepared but disabled by default because the hook surface is experimental. Deterministic scripts and CI remain the stronger enforcement layer.

