# Subagents Playbook

## Built-in subagent_types (Claude Code)

| subagent_type | Kind | Use for |
|---------------|------|---------|
| `Explore` | read-only explorer | bounded codebase question; specify thoroughness (quick / medium / very_thorough) |
| `Plan` | planner | step-by-step implementation plan, architectural tradeoffs |
| `general-purpose` | full tools | bounded implementation, reviewer role, multi-step research |
| `claude-code-guide` | docs | questions about Claude Code CLI, SDK, API |
| `codex:codex-rescue` | rescue | Codex fallback when Claude is stuck (defense-in-depth) |

## Use subagents when

- Codebase question is narrow and independent
- Implementation slice can be path-isolated
- Main session can keep making progress while the subagent runs

## Do NOT use subagents when

- Next step is blocked by the result (delegation adds latency without parallelism)
- Question is too broad (scope explodes)
- Two subagents might touch the same file (ownership conflict)

## Preflight (recommended)

```bash
python3 scripts/harness/subagent_planner.py plan \
    --role worker --owner worker-auth \
    --goal "implement auth slice" \
    --write-scope src/auth --write-scope tests/auth \
    --claim
```

- `dispatch_status=ready` → paste `dispatch_prompt` into `Agent(prompt=...)`.
- Conflicts → redesign owner/scope before launching.
- Use `--claim` to record ownership in `.claude/context/ownership.json`.

After subagent returns: `python3 scripts/harness/subagent_planner.py release --owner worker-auth`.

## Isolation (Agent tool native)

`worker` role defaults to `isolation: worktree` in `.claude/manifests/subagents.yaml`. When dispatching:

```
Agent({
  subagent_type: "general-purpose",
  isolation: "worktree",   # git worktree — auto-cleanup if no changes
  prompt: "...",
})
```

## Integration rule

Main session does NOT trust subagent output blindly. Before integrating:
1. `git diff` the subagent's changes
2. Run validation commands the subagent claims to have run
3. Check `remaining_risks` field in the subagent's report

## Required contract (from manifest)

Every worker dispatch prompt must cover:
- goal (one sentence)
- owner (unique id)
- read_scope (what it may read)
- write_scope (what it may write — enforced by ownership claim)
- stop_condition
- validation
- forbidden_paths (all protected paths by default)
