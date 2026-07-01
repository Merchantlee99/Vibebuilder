---
name: codex-skill-router
description: Vibebuilder Codex skill and plugin router. Use when a Codex task needs intent classification, automatic skill selection, read-only protection, current-docs detection, release/debug/review/design routing, or fixture-backed validation before coding, review, release, or harness improvement work.
---

# Codex Skill Router

## Overview

Use this skill to classify a natural-language Codex request before spending implementation tokens. It turns a request into a route, constraints, suggested skills, forbidden actions, and evidence obligations.

## Workflow

1. Run or mentally apply `scripts/classify_task.py` to classify the request.
2. Preserve the returned `constraints` across the whole turn.
3. Use the narrowest suggested skill set that satisfies the route.
4. Before claiming completion, satisfy the returned `evidence_required` list.
5. When route logic changes, add or update `fixtures/route_fixtures.jsonl` and run `scripts/route_eval.py --suite train` plus `--suite heldout`.

## Route Semantics

- `quick`: one-command checks, small explanations, current release-note lookups.
- `normal`: bounded implementation or docs edits with focused evidence.
- `deep`: architecture, backend contracts, evals, harness work, or read-only structure analysis.
- `ultra`: broad research, market/strategy, exhaustive analysis, or high-ambiguity harness changes.
- `design`: product UI, UX, onboarding, paywall, dashboard, checkout, or responsive visual work.
- `debug`: failing tests, crashes, wrong output, performance regressions, or root-cause analysis.
- `review`: code review, audit, red-team, regression/security review, or critique.
- `release`: launch, production, deployment, packaging, go/no-go, rollback, or readiness work.

## Constraint Rules

- `read_only=true`: do not edit, stage, commit, format, migrate, or run write-heavy commands.
- `current_docs_required=true`: use official/current sources before unstable claims.
- `product_ui=true`: use UI references and rendered evidence when implementation is in scope.
- `release_gate=true`: require gate status, risk inventory, rollback notes, and go/no-go posture.
- `security_sensitive=true`: include security/safety review and avoid exposing secrets.
- `skill_harness=true`: use fixture-backed validation before accepting route or skill changes.

## Resources

- `scripts/classify_task.py`: route classifier used by the skill.
- `scripts/route_eval.py`: regression test for route, constraint, and skill selection.
- `scripts/self_test.py`: py-compile and train/heldout eval wrapper.
- `fixtures/route_fixtures.jsonl`: train and held-out routing examples.
- `references/routing-contract.md`: readable contract for route output.
- `references/plugin-adoption.md`: how the repo-local plugin is laid out and adopted.

## Output Contract

Return:

- selected route.
- active constraints.
- suggested skill handoff.
- forbidden actions.
- evidence required.
- validation run or explicit reason validation was not run.
