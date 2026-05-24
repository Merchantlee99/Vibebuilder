---
name: harness-intake
description: Use when a user gives a new product, coding, review, debugging, or planning task in this Codex harness. Classifies tier, decides whether subagents/native features are useful, and fixes the initial contract before work starts.
---

# Harness Intake

Use this skill at the start of non-trivial work.

## Steps

1. Restate the goal, constraints, and done-when in one short block.
2. Classify the task:
   - `trivial`: small, low-risk, one obvious path.
   - `normal`: meaningful behavior or product change.
   - `high-risk`: auth, payments, security, migrations, infra, broad refactor, legal/compliance, destructive actions, or unclear blast radius.
3. Decide whether native features are useful:
   - subagents for bounded parallel planning, research, code mapping, review, or disjoint work.
   - worktree for broad/risky implementation.
   - browser for current docs or UI QA.
   - terminal for deterministic checks.
   - automation for waits, retros, stale review, or recurring audits.
4. For `normal+`, define required artifacts:
   - goal and non-goals
   - acceptance criteria
   - validation plan
   - rollback or recovery plan
   - review owner
5. Do not ask the user to run commands unless blocked. Run harness checks yourself when appropriate.

## Output Contract

Return:

- tier
- planned approach
- subagents/native features to use or skip
- key risks
- first action

