# Sealed Prompt — Meta-Audit (harness self-evaluation)

> TRUSTED prompt. Used only when `meta_supervisor.py` decides a meta-audit
> should run. Evaluates the harness itself, not the user's code. Immutable
> by AI without user approval.

## Context

The harness has 10 gates (see CLAUDE.md) + 5-stage pipeline + 4-layer
architecture (workflow / pipeline / guardrail / self-evolving).

The supervisor triggers this audit when evidence suggests drift: repeated
same-gate blocks, plan-revision bursts, rollback/hotfix signals,
protected-path probes, cumulative event threshold, or explicit user request.

## Your role

You are evaluating **the harness**, not the user's project. Your question:
**"Is the harness catching what it should, or is it missing things, or is
it causing friction out of proportion to the risk it prevents?"**

Be willing to say "this gate is useless" or "this gate blocks more than it
catches."

## What to read

1. The triggering evidence packet (events.jsonl excerpts + learnings.jsonl
   excerpts + git log excerpts) handed to you below.
2. The current hooks in `.claude/hooks/`.
3. `CLAUDE.md` / `AGENTS.md` / `ETHOS.md`.
4. The last 4-axis version (`runtime.json → framework_version`).

## Answer exactly this structure

```
Overall: harness-healthy | harness-drifting | harness-broken

Per-gate assessment (for each gate that fired or should have fired):

Gate ①  — fired: N   useful blocks: M   false blocks: K
  Assessment: <1-2 sentences>
  Recommended change: <specific, bounded — never "rewrite">

Gate ②  — ...
(etc. for each gate covered)

Per-layer assessment:

Layer 1 (Workflow/skills):
  - usage rate: <high|medium|low>
  - drift signal: <which skills became stale>
  - Recommendation: <bounded>

Layer 2 (Pipeline):
  - stage transition health: <where stuck>

Layer 3 (Guardrail):
  - block accuracy: <useful blocks / total>

Layer 4 (Self-evolving):
  - proposals generated: N   user approved: M   rejected: K
  - Drift signal: <if auto-proposals are trending wrong direction>

Cross-cutting patterns:

1. <pattern>
   Evidence: <event ids or timestamps>

2. ...

Gates that should exist but do not:
- <proposed gate>
  Failure mode it would catch: <concrete>
  Minimum implementation cost: <hook file + ~N lines>

Gates that should be removed or relaxed:
- <gate>
  Why: <evidence it catches less than it costs>

Proposed threshold adjustments (if any):
- trivial LOC: current=20 → proposed=X because <evidence>
- normal LOC:  current=100 → proposed=Y because <evidence>

Decision the user must make:
<1-3 bullets summarizing which changes REQUIRE user approval before
 the supervisor applies them. Nothing here auto-applies.>
```

## Forbidden output

- "하네스가 잘 작동하고 있습니다" without citing specific events that prove it
- Proposing sweeping rewrites — audits propose bounded adjustments
- Recommending threshold raises to reduce gate firing, unless evidence shows
  the missed blocks cost less than the friction saved
- Deciding anything on the user's behalf — all changes require explicit
  user approval

## Correlated-blindness check

The human user and you (Claude) may share blind spots when your
conclusions trace back to the same training data or same recent context.
If a parallel review ran (another isolated Claude session or the human user),
compare conclusions. Every point of agreement is a candidate for independent
verification — especially when both arrive via similar reasoning paths.
Flag agreements explicitly:

```
Agreements with parallel reviewer (verify independently before acting):
- <point>
```

## Write your output to

`.claude/audits/meta-audit-<YYYYMMDDTHHMMSS>.md`

If a parallel reviewer is unavailable, write instead:
`.claude/audits/meta-audit-pending-<YYYYMMDDTHHMMSS>.md` with a single line
explaining why the audit could not complete. Gate ⑤ will surface this at
next session start as pending, and harness changes stay frozen until the
audit completes.
