# MCP Playbook

## When to connect an MCP server

| Need | Server | Why |
|------|--------|-----|
| Web page interaction (DOM) | `claude-in-chrome` | DOM-aware, much faster than pixel clicks |
| Native desktop app control | `computer-use` | Only when browser/terminal insufficient |
| Sandboxed file access beyond cwd | `filesystem` | Explicit allowlist, no full disk access |
| Recurring task / heartbeat | `scheduled-tasks` | Pairs with Automation-Intent.md |
| Library docs lookup | `context7` (optional) | Prefer over WebFetch for SDK/framework queries |
| Design tool integration | `pencil` / figma MCP (domain-specific) | Only when design work is in scope |

## Tool escalation order (read + act on web)

1. **`WebFetch` / `WebSearch`** — read-only, fastest. For docs and linked pages.
2. **`claude-in-chrome`** — when DOM interaction or real browser session needed.
3. **`computer-use`** — only for GUI-only flows, auth obstacles, or desktop-app work.

Skipping steps wastes time and permissions. `WebFetch` is ~100x faster than a browser session for a doc lookup.

## Permission scoping

- Never grant MCP full-repo write without reading the server's source/manifest first.
- Prefer per-tool permission in `.claude/settings.local.json` over blanket allow:
  ```json
  "permissions": {
    "allow": [
      "mcp__filesystem__read_text_file",
      "mcp__filesystem__list_directory"
    ],
    "deny": [
      "mcp__filesystem__edit_file"
    ]
  }
  ```
- If the MCP server can run arbitrary code (shell, python eval, db write), treat like Bash — explicit allowlist only.

## Trust boundary (Gate ⑨)

MCP responses are **external data**. The harness Gate ⑨ scans `WebFetch` / `WebSearch` / `Bash` for prompt-injection patterns; **MCP server responses are now also scanned** (see `post_tool_use.py:gate_9_trust`). Patterns flagged:

- `ignore previous instructions`
- `you are now a <role>`
- `<system>` / `</system>` fake trust tags
- `new instructions:` markers

Flags are advisory (logged, not blocked). If an MCP server repeatedly triggers Gate ⑨, audit the server — it may be a supply-chain risk.

## Audit

Run `python3 scripts/harness/mcp_audit.py` to list currently configured MCP servers, their permissions, and their last-use frequency from events.jsonl.

## Rules

1. No secret-bearing MCP config in `.claude/mcp.json` if the repo is public. Use env-var refs.
2. Prefer MCP over shelling out to CLI when semantics match (e.g., `mcp__filesystem__read_text_file` > `Bash(cat ...)`).
3. If both a dedicated MCP and `computer-use` could do the job, dedicated MCP wins on speed and reliability.
