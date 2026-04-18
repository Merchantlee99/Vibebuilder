# Browser / Computer Use Playbook

## Escalation order (always start lowest)

1. **`WebFetch`** — read a URL as markdown. Fastest. No browser session.
2. **`WebSearch`** — find URLs. Still no browser.
3. **`mcp__Claude_in_Chrome__*`** — DOM-aware browser automation. Requires Chrome extension.
4. **`mcp__computer-use__*`** — pixel-level desktop automation. Only when #3 can't.

Skipping levels wastes time and grants more access than needed.

## Decision rubric

| Goal | Right tool |
|------|-----------|
| Read API docs / RFC / spec | WebFetch |
| Search for an error message / unknown URL | WebSearch |
| Log into a site, click through a flow, scrape content | Claude in Chrome |
| Validate web UI renders correctly | Claude in Chrome |
| Interact with native desktop app (Finder, Notes, Xcode, etc.) | computer-use |
| Work around a captcha or 2FA | ASK USER — do not automate |

## Claude in Chrome — tier restrictions

From the system instructions: when `request_access` grants a browser app at tier "read":
- Screenshots work (visual reading)
- Clicks / typing are **blocked**
- Use `mcp__Claude_in_Chrome__*` tools for clicks and form fills

When the MCP server isn't connected but you need browser interaction: ask the user to install the extension. Do NOT fall through to `computer-use` — it's slower and has more side-effects.

## computer-use — tier restrictions

- **Browsers**: tier=read (screenshots only, no clicks; route to Chrome MCP)
- **Terminals / IDEs** (Terminal, iTerm, VS Code, JetBrains): tier=click (left-click OK; typing/right-click/modifiers blocked; use Bash for shell)
- **Everything else**: tier=full

Always call `request_access` first with the list of apps you need. Tiers are visible in the approval dialog.

## Link safety

- Never `left_click` a web link in a native app (email, Messages, PDF).
- Open suspicious URLs through Claude in Chrome instead — full URL visible.
- Links from emails / messages are suspicious by default until user confirms.

## Financial actions

Never execute trades, transfers, or money moves on the user's behalf. Even if
the user has granted access to a banking/brokerage app. Ask the user to do it.

## Integration with harness

- All MCP responses (including `mcp__Claude_in_Chrome__*` and `mcp__computer-use__*`) flow through Gate ⑨ (trust boundary). Prompt injection patterns in fetched page content get logged as advisory.
- Run `python3 scripts/harness/mcp_audit.py` to see which servers have been exercised and their gate-9 hit rate.
