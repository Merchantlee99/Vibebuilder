---
name: skillify-proposal
description: Use when a repeated failure, repeated success pattern, or recurring workflow should become a proposed Codex skill after audit, not automatic self-modification.
---

# Skillify Proposal

Use this for human-in-the-loop harness evolution.

## Rules

- Do not silently add a new skill as part of normal work.
- Create a proposed skill when the same failure or workflow appears repeatedly.
- Proposed skills live under `harness/proposed-skills/` until reviewed.
- Promotion requires a clear trigger, non-overlap with existing skills, examples, and a validation checklist.

## Proposal Checklist

- Problem this skill prevents or accelerates.
- Trigger phrases and non-trigger cases.
- Expected output contract.
- Required scripts or references, if any.
- Routing risks and overlap with existing skills.
- Test or review method.

## Output Contract

Return a concise proposal, not a final installed skill, unless the user explicitly approves promotion.

