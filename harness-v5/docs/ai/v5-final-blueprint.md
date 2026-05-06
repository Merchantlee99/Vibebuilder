# Codex Harness v5 Final Blueprint

## Position

v5 is not a visual-first harness. It is an implementation-first Codex harness with a UI evidence overlay and an audited self-improvement loop.

```text
v5 = v2 implementation performance
   + v3 high-risk strictness
   + v4 simplicity and UI discipline
   + runtime/visual evidence
   + Hermes-style learning, gated by review
```

The default path must stay fast. Heavy visual, strict, or learning workflows activate only when the task profile justifies them.

## Non-Negotiables

- Coding correctness outranks visual QA.
- Screenshot-only completion is forbidden for `normal+` work.
- High-risk routing overrides UI routing.
- Scripts validate objective evidence; they do not decide architecture, taste, or product correctness.
- Subagent output is never final.
- Memory can suggest, but cannot silently change active policy.
- Every non-applicable UI gate needs `not_applicable_reason` plus residual risk.

## Architecture

```text
harness-v5/
  AGENTS.md
  README.md
  ETHOS.md

  .codex/
    config.toml
    hooks.json
    agents/
      code-mapper.toml
      docs-researcher.toml
      reviewer.toml
      security-auditor.toml
      browser-qa.toml
      visual-reviewer.toml
      learning-curator.toml
    hooks/

  .agents/skills/
    harness-intake/
    plan-before-change/
    karpathy-engineering/
    implementation-evidence/
    ui-evidence/
    browser-qa/
    visual-review/
    accessibility-audit/
    critical-review/
    eval-loop/
    memory-curation/
    skillify-proposal/
    close-session/

  harness/
    runtime.json
    model_policy.json
    strict_policy.json
    risk_manifest.json
    evidence/
      evidence.jsonl
      evidence-matrix.json
      artifacts/
    visual/
      screenshots/
      reports/
      layout-maps/
      axe/
    evals/
      runs/
    reviews/
    context/
    telemetry/
    proposed-skills/
    audits/

  docs/ai/
  templates/
  scripts/harness/
  tests/
```

`.codex/` stays static. Mutable state belongs under `harness/` and `docs/ai/`.

## Task Profiles

The orchestrator drafts a task profile before meaningful edits. Scripts may challenge objective inconsistencies, but do not replace orchestrator judgment.

```json
{
  "kind": "bugfix | feature | refactor | ui | docs | security | migration | runtime-debug | learning",
  "tier": "trivial | normal | high-risk",
  "surface": "backend | frontend | fullstack | non-web-ui | docs | harness",
  "changed_paths": [],
  "required_gates": [],
  "ui_evidence": "required | optional | not-applicable",
  "strict_required": false,
  "not_applicable_reason": "",
  "residual_risk": ""
}
```

## Task / Gate Matrix

| Work type | Default route | Required evidence | Required gates |
| --- | --- | --- | --- |
| Trivial code | Main Codex direct | Command/result summary | `gate.py --tier trivial` |
| Normal code | v2 flow + simplicity discipline | changed files, tests/build/typecheck, review | `quality_gate.py`, `review_gate.py`, `session_close.py` |
| Feature/fullstack | plan + implementation evidence | acceptance checks, domain validation, tests | normal gates + targeted runtime evidence |
| Broad refactor | code map + ownership claims | affected paths, regression tests, rollback note | `subagent_planner.py check`, `simplicity_gate.py`, review |
| UI visual-only | UI evidence overlay | screenshot, viewport/state, DOM/layout notes | `ui_evidence_gate.py`, design review |
| Frontend logic | implementation-first + UI evidence | tests/build + browser scenario + screenshot if rendered behavior changed | normal gates + `runtime_evidence_gate.py` + `ui_evidence_gate.py` |
| High-risk | v3 strict path | risk rationale, rollback, independent review, event verification | `strict_gate.py`, security review, quality gate |
| High-risk UI | high-risk first, UI second | strict evidence + screenshot/UX risk evidence when safe | strict gates + UI evidence gate |
| Runtime/debug | reproduce before fix | repro steps, logs, server URL, command exits | `runtime_evidence_gate.py`, review when normal+ |
| Non-web UI | adapter/manual evidence | platform screenshot/video, state notes, accessibility limits | `non_web_ui_evidence_gate.py` or residual risk |
| Learning/improvement | proposed only | source events, repeated pattern, test fixture | `learning_gate.py`, `skillify_audit.py`, review |

## Script Boundary

Scripts should block only objective missing evidence or objective policy violations.

Good script duties:

- Classify risk hints and changed surface hints.
- Detect UI file, auth, payment, secret, migration, release, or destructive path changes.
- Check required evidence exists and has valid shape.
- Run or verify test/build/lint/typecheck command records.
- Enforce subagent ownership claim conflicts.
- Verify review artifact independence.
- Audit proposed memory/skill promotion.

Bad script duties:

- Decide visual taste.
- Choose architecture.
- Replace code review.
- Declare a screenshot good.
- Auto-promote learnings into active rules.
- Block non-web UI only because browser evidence is absent.
- Execute irreversible external operations.

## Evidence Schema

Evidence is append-only JSONL, with artifacts stored by session/task id.

```text
harness/evidence/evidence.jsonl
harness/evidence/artifacts/<task-id>/
```

Required record shape:

```json
{
  "schema_version": 1,
  "id": "ev_20260506_001",
  "task_id": "task_or_session_id",
  "kind": "command | runtime | visual | accessibility | layout | review | risk | learning",
  "tier": "normal",
  "status": "pass | fail | warning | not-applicable",
  "actor": "main-codex",
  "cwd": "/repo",
  "changed_files": ["src/app.tsx"],
  "command": "pnpm test",
  "exit_code": 0,
  "route": "/settings",
  "viewport": "390x844",
  "state": "error",
  "artifacts": [
    {
      "type": "screenshot",
      "path": "harness/evidence/artifacts/task/settings-mobile-error.png",
      "sha256": "..."
    }
  ],
  "summary": "Settings error state renders without horizontal overflow.",
  "not_applicable_reason": "",
  "residual_risk": "No screen reader manual pass."
}
```

Evidence gates validate presence, shape, artifact paths, hashes, route/state/viewport context, and residual risk. They do not judge taste.

## UI Evidence Policy

UI evidence is required when rendered UI behavior, layout, interaction, or user-facing state changes. It is optional for copy-only or aria-only trivial fixes unless the user asks for visual QA. It is not applicable for pure backend/docs tasks.

Blockers:

- Primary action invisible or unreachable.
- Horizontal overflow on supported viewport.
- Critical text clipped or hidden.
- Console/runtime error on target route.
- Unlabeled critical interactive control.
- Severe axe/accessibility violation on primary flow.
- Destructive or irreversible UI action is visually ambiguous.

Warnings:

- Minor spacing drift.
- Noncritical contrast issue.
- One-off arbitrary Tailwind value in prototype code.
- Pixel diff on unstable full-page screenshot.
- Missing Storybook coverage in a project that does not already use Storybook.

Default UI checks:

```text
ui-static:
  token drift, raw hex/rgb, arbitrary Tailwind values, obvious CSS lint

ui-render:
  Playwright route open, desktop/mobile screenshots, console errors,
  overflow, primary action visibility, focusability, touch target basics

ui-accessibility:
  axe checks where available, accessible names, keyboard path notes

ui-review:
  visual reviewer + customer UX red-team over the same evidence bundle
```

Screenshot diffing is selective. Use it for stable components, key flows, or explicit regression baselines. Do not make full-page pixel diff a default blocker.

## Sensitive And Non-Web UI

Sensitive UI may use redacted screenshot, cropped screenshot, text evidence, or no screenshot with residual risk. Sensitive surfaces include auth tokens, customer data, billing, secrets, private file paths, healthcare/legal/financial records, and admin screens.

Non-web UI uses platform evidence:

- Tauri/Electron: app screenshot/video plus state fixture and logs.
- Native mobile/desktop: simulator screenshot, accessibility inspector notes when available.
- CLI/TUI: terminal transcript and layout snapshot.
- Canvas/WebGL/game: screenshot/video plus interaction assertions.
- Figma/design-only: frame screenshot plus design-token/state notes.

Browser QA is an adapter, not the universal evidence path.

## Subagent Policy

Default subagents are read-only. Writing workers require explicit write scope, stop condition, ownership claim, and worktree preference.

Recommended roles:

- `code_mapper`: affected code path and ownership.
- `docs_researcher`: current official docs and version-sensitive behavior.
- `reviewer`: correctness, regression, tests, maintainability.
- `security_auditor`: high-risk trust boundaries.
- `browser_qa`: runtime route and browser evidence.
- `visual_reviewer`: hierarchy, density, state clarity, UI evidence critique.
- `learning_curator`: repeated failure clustering and proposed improvement review.

Rules:

- Max depth 1.
- No producer self-review.
- Subagent output is evidence, not final decision.
- The orchestrator owns final synthesis.
- Fan-out only when it reduces wall-clock time, context noise, or risk.

## Hermes-Style Self-Improvement

Self-improvement is audited improvement of workflows, not autonomous self-modification.

```text
observe -> cluster -> diagnose -> propose -> test -> review -> promote -> monitor
```

1. Observe failures, retries, skipped gates, review findings, escaped regressions, false positives, and successful repeat workflows.
2. Cluster repeated patterns with source event references.
3. Diagnose one small change: routing rule, skill patch, template patch, or deterministic gate.
4. Test against a golden task or fixture.
5. Write only to `harness/proposed-skills/` or `harness/audits/`.
6. Require `learning_gate.py`, `skillify_audit.py`, and independent review before promotion.
7. Promote only by explicit approval or project policy.
8. Monitor false trigger rate and escaped regression rate.

Memory record requirements:

- source event id or evidence id
- repeated validated occurrence count
- confidence
- expiry/review date
- proposed action
- reviewer verdict

Memory can influence prompts only after curation. Raw learning logs never become active rules.

## Performance Metrics

v5 must improve total harness performance, not only UI quality.

Track:

- time_to_first_edit
- gate_runtime_ms
- false_positive_gate_blocks
- gate_bypass_count and reason
- implementation_validation_coverage
- review_reject_rate
- escaped_regression_count
- visual_regression_count
- skill_false_trigger_count
- repeated_failure_count

`benchmark_harness.py` should compare v5 template overhead against v4 on golden tasks:

- trivial one-file code fix
- normal backend bugfix
- normal frontend UI change
- broad refactor
- high-risk auth/payment change
- repeated failure leading to proposed skill

v5 fails the benchmark if non-UI code tasks become materially slower without catching additional real risk.

## Minimum Viable Implementation Order

1. Copy v4 backbone and preserve v2/v3 scripts.
2. Add compact `AGENTS.md` with task profile, high-risk override, script boundary, and evidence rules.
3. Add `harness/evidence/evidence-matrix.json`.
4. Add `implementation_gate.py` and `evidence_log.py`.
5. Add `ui_evidence_gate.py` with shape validation only.
6. Add Playwright/axe/layout checks as optional adapters.
7. Add `memory_guard.py` and proposed-skill review templates.
8. Add benchmark golden tasks before tightening gates.
9. Only then add visual diffing or Storybook adapters.

## Red-Team Findings Incorporated

- Visual QA cannot replace implementation validation.
- UI evidence must be scoped by task profile.
- Scripts are deterministic validators, not semantic routers.
- High-risk UI follows high-risk rules first.
- Browser QA cannot be the only UI adapter.
- Screenshots need redaction/no-screenshot policy.
- Memory needs provenance, expiry, quarantine, and review.
- Gates need blocker/warning/advisory severity.
- `not_applicable_reason` is required for skipped UI evidence.

## Final Review Checklist

- [ ] `AGENTS.md` is compact and operational.
- [ ] Task profile exists before normal+ edits.
- [ ] High-risk override precedes UI/design routing.
- [ ] Trivial fast path remains fast.
- [ ] Implementation gates and UI evidence gates are separate.
- [ ] Screenshot-only completion is forbidden.
- [ ] Non-web UI evidence path exists.
- [ ] Sensitive screenshot redaction/no-screenshot policy exists.
- [ ] Subagent independence and ownership are enforced.
- [ ] Memory promotion requires evidence and review.
- [ ] Gate severity avoids false-positive overload.
- [ ] Script boundaries are explicit.
- [ ] `not_applicable_reason` and residual risk are supported.
- [ ] Benchmark golden tasks guard v2/v3/v4 performance.
