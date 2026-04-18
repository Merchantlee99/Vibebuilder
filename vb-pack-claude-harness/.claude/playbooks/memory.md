# Memory Playbook

## Three memory systems (decision tree)

```
Is the info a RULE / INVARIANT that governs behavior here?
    YES → CLAUDE.md (project-level, committed)
    NO  → next

Is the info PROJECT-specific context (decisions, active work, gaps)?
    YES → .claude/memory/ (user-local, gitignored) OR the 6 required
          artifacts (Prompt/PRD/Plan/Implement/Documentation/Subagent-Manifest)
    NO  → next

Is the info CROSS-project (user preferences, style, role)?
    YES → global auto memory (~/.claude/projects/-*/memory/)
    NO  → probably ephemeral — do not persist
```

## System comparison

| System | Scope | Committed? | Auto-loaded? | Size hint |
|--------|-------|-----------|-------------|----------|
| `CLAUDE.md` | project | yes | every session start | keep under 200 lines |
| `.claude/memory/*.md` | project, user-local | no (gitignored) | no — manually read | per-file |
| Required artifacts | project | yes | manually read | per-template |
| Global auto memory | cross-project | no | `MEMORY.md` index is auto-loaded | index < 150 chars/line |

## When to write to global auto memory

- User's role, experience level, preferred style
- Recurring feedback ("prefer X over Y")
- Past incidents ("we got burned by Z last quarter")
- External system references ("bugs tracked in Linear project ABC")

See the Auto memory section in the system prompt for schema + examples.

## When NOT to persist anywhere

- Current-turn-only task details
- Easily-derivable info (architecture, file paths — read the code instead)
- Debugging steps (the commit message has it)
- Anything already in CLAUDE.md

## CLAUDE.md hygiene

- CLAUDE.md loads on every session start → keep tight
- New rules go here only after the user explicitly agrees it's a RULE
- Decisions / rationale for rules go in `ETHOS.md`, not CLAUDE.md
- Past incidents / failure patterns go in `.claude/learnings.jsonl` (auto), not CLAUDE.md

## Session continuation

For tasks spanning multiple sessions:
1. `Documentation.md` → "Restart point" section (persistent, committed)
2. `Implement.md` → "Current slice" (persistent, committed)
3. `Automation-Intent.md` → scheduled heartbeats (see automation.md)
4. `.claude/learnings.jsonl` → anything that failed (auto-recorded by post_tool_use hook)

None of these rely on the chat transcript.
