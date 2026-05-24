---
name: browser-qa
description: Use when a local or deployed browser route must be opened, reproduced, interacted with, screenshot, or checked for console/runtime errors. Do not use when static tests fully cover the change.
---

# Browser QA

Use browser QA for rendered behavior and state verification.

## Steps

1. Start or identify the dev server.
2. Visit the exact route.
3. Check target viewport and state.
4. Exercise the user action.
5. Capture screenshot or runtime notes.
6. Record console errors and residual risk.

## Output Contract

Return route, viewport, state, action, observed result, artifacts, console findings, and unverified states.
