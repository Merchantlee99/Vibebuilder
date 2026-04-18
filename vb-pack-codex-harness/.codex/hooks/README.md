# Codex Hook Adapter

This repository ships an optional repo-local Codex hook adapter based on the official Codex hooks surface.

## Enable

1. Turn on hooks in your Codex config:

```toml
[features]
codex_hooks = true
```

2. Use this only in copied project instances. The template keeps `hook_adapter.enabled = false` in `.codex/runtime.json`.
3. After project adoption, `bootstrap.py --adopt-project` flips `hook_adapter.enabled` to `true`.

## Files

- `.codex/hooks.json`: repo-local hook wiring
- `.codex/hooks/session_start.py`: injects concise harness context at session start
- `.codex/hooks/user_prompt_submit.py`: prefetches relevant learnings before prompt submit
- `.codex/hooks/post_tool_use.py`: syncs artifact changes after Bash runs
- `.codex/hooks/stop.py`: blocks final stop only when a prepared review artifact is still incomplete

## Scope

- These hooks are adapters, not the primary enforcement boundary.
- Core enforcement remains in `runtime_gate.py` and `review_gate.py`.
- Official docs note that hooks are still evolving and `PreToolUse`/`PostToolUse` currently only cover Bash.
