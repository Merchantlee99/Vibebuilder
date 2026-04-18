# Sealed Prompt — Failure Analysis (Layer 2 stage: postmortem)

When something fails repeatedly (Gate ③ trigger: same failure 3+ times), you
perform structured root-cause analysis and record a learning.

## Task

1. Read the most recent N failure events from `.claude/events.jsonl`.
2. Read the involved files at the commits in question.
3. Classify the failure using the `FAILURE_TAXONOMY` in
   `scripts/harness/learning_log.py`.
4. Write a postmortem that separates **proximate cause** (what broke) from
   **root cause** (why it broke) from **systemic cause** (why this class of
   bug is possible here).

## Return

```
# Postmortem — <YYYY-MM-DD> — <slug>

## Summary (1 paragraph)

## Timeline
- T0 <ts>: <what happened>
- T1 <ts>: <next step>
- ...

## Proximate cause
<what literally broke>

## Root cause
<why the proximate cause was possible>

## Systemic cause
<why this class of bug is possible in this codebase / workflow>

## Pattern classification
FAILURE_TAXONOMY: <known vocabulary or "proposed: <new-pattern>">

## Did existing learnings.jsonl predict this?
- <entry ts> — <how it related, or "no prior warning">

## Fix recommendation
- Immediate: <what to change now>
- Systemic: <what to change to prevent this class>
- Detection: <what signal would have caught this earlier>

## Learning to record
pattern: <taxonomy slug>
mistake: <1 sentence>
fix: <1 sentence>
```

## Rules

- Do NOT modify production code in this stage.
- Learning entry MUST be added via:
  ```
  python3 scripts/harness/learning_log.py append <gate> <pattern> "<mistake>" "<fix>"
  ```
- If the pattern is not in FAILURE_TAXONOMY, propose it explicitly and write
  to `.claude/audits/taxonomy-proposals.md` for user approval.

Write to `.claude/audits/postmortem-<YYYYMMDDTHHMMSS>.md`.
