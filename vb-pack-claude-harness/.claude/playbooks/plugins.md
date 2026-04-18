# Plugins Playbook

## Why plugins matter to this harness

- Plugins extend Claude Code with skills, MCP servers, and agent definitions.
- Reproducibility: `.claude/plugins.lock` pins which plugins this project expects. Session-start can detect drift.
- Layering: harness core stays minimal; plugins add domain-specific capabilities.

## Recommended plugins (solo harness)

See `.claude/plugins.lock` for the canonical list. Highlights:

### Defense-in-depth

- **`codex:rescue`** — Delegates to Codex when Claude is stuck (repeated gate blocks, user asks for second opinion).
- **`codex:setup`** — Bootstraps Codex CLI availability.

### Documentation & Q&A

- **`claude-code-guide`** — Authoritative on Claude Code features, hooks, SDK, API.

### Memory & skills

- **`anthropic-skills:consolidate-memory`** — Merges duplicate memories, prunes stale.
- **`anthropic-skills:skill-creator`** — Promotes `_evolving/` → `_manual/`.
- **`anthropic-skills:schedule`** — Cron-style scheduled agents (pairs with Automation-Intent).

## When to install a new plugin

1. You find yourself running the same multi-step workflow 3+ times.
2. A Claude Code feature is available via plugin that the harness could leverage.
3. A team-specific workflow needs encapsulation.

## When NOT to install

- One-shot task.
- The functionality is already in the harness (don't duplicate).
- The plugin is not from a trusted source — read the source first.

## Drift detection (optional)

`session_start.py` can diff active plugins vs `.claude/plugins.lock`:
- Plugins in `locked` but not active → warn "missing pinned plugin"
- Plugins active but not in `locked` or `suggested` → advisory "unpinned plugin in use"

This is advisory-only; it does not block.

## Installing

```
/plugin install <name>
```

After install, add to `.claude/plugins.lock.locked[]` if you want to pin it project-wide.

## Plugin vs skill vs MCP

- **Skill**: prompt-time capability registered by name. Invoked via the Skill tool.
- **MCP**: tool-server over stdio / http. Adds `mcp__*` tools to Claude's toolkit.
- **Plugin**: distribution mechanism that can bundle skills + MCP + agents.

When shipping your own: prefer skill if it's prompt-only, MCP if it needs side-effects (fs, net, db), plugin if it's multiple of the above.
