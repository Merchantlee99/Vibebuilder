# Hooks Recipes

## Registered hooks

| Event | Hook | Purpose |
|-------|------|---------|
| `SessionStart` | `session_start.py` | Load learnings, snapshot context, circuit-check |
| `UserPromptSubmit` | `user_prompt_submit.py` | Inject top-5 relevant learnings |
| `PreToolUse` (Edit/Write) | `pre_tool_use.py` | Gate ① / ⑥ / ⑦ / ⑩ + Gate ② Pre enforcement |
| `PostToolUse` (Edit/Write/Bash) | `post_tool_use.py` | Gate ② review-needed / ④ test runner / ⑧ claim / ⑨ trust |
| `Stop` | `stop.py` | End-of-turn cleanup, rotation check |

## Optional events (not registered by default)

- `PreCompact` — fire before Claude Code auto-compacts history. Use to persist in-flight state to `.claude/ephemeral/` before summary.
- `Notification` — fire when Claude Code shows a notification. Use to log external interruptions.

## Adding a hook

1. Write `.claude/hooks/<name>.py` (must be executable, read JSON from stdin).
2. Register in `.claude/settings.local.json` under `hooks.<Event>`.
3. Add to `EXPECTED_HOOKS` in `scripts/harness/self_test.py`.
4. Add to `HOOK_NAMES` in `scripts/harness/hook_health.py` (so circuit breaker tracks it).
5. Wrap `main()` with circuit breaker `circuit_check` / `record_success` / `record_failure`.

## Circuit breaker cheat sheet

```bash
python3 scripts/harness/hook_health.py status                # list all
python3 scripts/harness/hook_health.py disable pre_tool_use  # maintenance mode
python3 scripts/harness/hook_health.py reset pre_tool_use    # back to ok
```

- `manual` disable → fail-open (pass-through)
- `tripped` (3 consecutive failures) → fail-closed for pre_tool_use (Layer 3 can't silently drop)

## Emit patterns

```python
# From inside a hook:
from common import emit_continue, emit_block

emit_continue(event_name="PreToolUse")           # exit 0, no message
emit_continue(system_message="FYI", event_name="PreToolUse")  # exit 0 with note
emit_block("reason for block")                   # exit 2, blocks the tool call
```

## systemMessage vs additionalContext

- `systemMessage` — shown to the user (blue info banner in Claude Code)
- `additionalContext` (via `hookSpecificOutput.additionalContext`) — injected into Claude's prompt, not visible to user

Use `systemMessage` for user-facing warnings, `additionalContext` for state that Claude needs to act on.

## Do not

- Do NOT modify events.jsonl / learnings.jsonl directly from a hook — use the `event_log` / `learning_log` modules so format and rotation are consistent.
- Do NOT emit_block unconditionally from a hook — think about recovery path; user must be able to unblock.
- Do NOT do network calls in hooks (timeouts freeze the tool).
