---
name: implementation-evidence
description: Use when completing normal or high-risk code work to collect command, test, build, typecheck, runtime, review, and residual-risk evidence before claiming completion. Do not use for trivial one-line edits unless validation is ambiguous.
---

# Implementation Evidence

Use this skill before finalizing `normal+` code work.

## Steps

1. State the task id and changed files.
2. Record commands run, exit codes, and key result summaries.
3. Include runtime reproduction when behavior cannot be proven by static tests.
4. Attach independent review evidence for `normal+` work.
5. Record `not_applicable_reason` for any skipped expected validation.
6. Record residual risk plainly.

## Output Contract

Return:

- task id
- command evidence
- runtime evidence if relevant
- review evidence
- skipped checks with reasons
- residual risk

Do not claim correctness from code inspection alone when tests or runtime checks are practical.
