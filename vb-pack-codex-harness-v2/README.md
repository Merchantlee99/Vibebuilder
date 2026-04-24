# Codex Harness v2

Codex Harness v2 is a Codex-only operating framework for long-running product and software work. It is designed for natural-language use: the user describes the goal, and Codex uses the harness rules to decide when to plan, spawn subagents, use worktrees, run terminal checks, open browser research, schedule automations, and require independent review.

This repository is a template, not an activated project instance. The framework is safe to inspect, copy, and adapt before enabling stronger enforcement.

## Design Goals

- Keep Codex native: use `AGENTS.md`, `.codex/config.toml`, `.codex/agents/*.toml`, and `.agents/skills`.
- Keep `AGENTS.md` thin and directive; move reusable workflows into skills.
- Keep `.codex` as the static control plane; put mutable runtime state under `harness/` and `docs/ai/`.
- Make subagents useful but bounded: read-only agents can fan out; writing workers need explicit ownership and usually a worktree.
- Enforce completion with gates, not trust: plan gate, scope gate, review gate, finish gate, and optional hook/CI integration.
- Preserve natural-language operation: users should not need to remember commands during normal work.

## Harness Layers

| Layer | Files | Purpose | Strength |
| --- | --- | --- | --- |
| Steering | `AGENTS.md` | Default Codex behavior and escalation rules | Advisory |
| Native config | `.codex/config.toml` | Thread fan-out limits and optional hooks | Medium |
| Custom agents | `.codex/agents/*.toml` | Role-specific subagents with sandbox defaults | Medium |
| Skills | `.agents/skills/*/SKILL.md` | Reusable workflows loaded by intent | Medium |
| Gates | `scripts/harness/gate.py` | Deterministic checks before completion | Strong |
| Hooks | `.codex/hooks/*.py` | Optional real-time guardrails | Medium, experimental |
| CI | `scripts/harness/self_test.py` | Repository-level validation | Strong |
| Scoring | `scripts/harness/score.py` | Measures readiness against 9.5 target | Strong |

## Default Workflow

1. User gives a natural-language task.
2. Main Codex acts as orchestrator and classifies the task as `trivial`, `normal`, or `high-risk`.
3. For `normal+` work, Codex fixes goal, constraints, owner, validation, and rollback before editing.
4. For broad or risky work, Codex uses read-only subagents first: `pm_strategist`, `docs_researcher`, `code_mapper`, `task_distributor`, and red-team agents as needed.
5. Implementation is done by the main thread or bounded workers with explicit write scopes.
6. Completion requires validation and, for `normal+`, an independent review outcome.
7. Repeated failures become proposed skills, not silent self-modification.

## Directory Layout

```text
.
├── AGENTS.md
├── README.md
├── ETHOS.md
├── .codex/
│   ├── config.toml
│   ├── agents/
│   └── hooks/
├── .agents/
│   └── skills/
├── harness/
│   ├── runtime.json
│   ├── context/
│   ├── reviews/
│   ├── telemetry/
│   ├── proposed-skills/
│   └── audits/
├── docs/ai/
├── templates/
├── scripts/harness/
└── tests/
```

## Verification

Run the structural checks:

```bash
python3 scripts/harness/bootstrap.py
python3 scripts/harness/self_test.py
python3 -m unittest discover -s tests -q
```

Run the advisory gate:

```bash
python3 scripts/harness/gate.py all --tier trivial
python3 scripts/harness/gate.py all --tier normal --template
```

Operational helpers:

```bash
python3 scripts/harness/review_gate.py prepare --tier normal --producer main-codex
python3 scripts/harness/review_gate.py finalize --review-file harness/reviews/review-YYYYMMDDTHHMMSSZ.md
python3 scripts/harness/subagent_planner.py plan --role worker --owner worker-auth --goal "auth slice" --write-scope src/auth --claim
python3 scripts/harness/automation_planner.py scan
python3 scripts/harness/skillify_audit.py all
python3 scripts/harness/score.py --min-score 95
```

## Enforcement Model

The template starts in `advisory` mode. A copied real project can move toward stronger enforcement by:

- Keeping runtime state in `harness/runtime.json`.
- Enabling `.codex/hooks.json` by setting `codex_hooks = true`.
- Running `scripts/harness/gate.py all --tier normal` before completion.
- Using `review_gate.py finalize` to block self-review and pending verdicts.
- Using `subagent_planner.py --claim` to prevent write-scope collisions.
- Auditing automation intents and proposed skills before promotion.
- Adding CI or branch protection that runs `scripts/harness/self_test.py` and the relevant gate.
- Running `scripts/harness/session_close.py` before final completion on real project work.

Hooks are intentionally optional because Codex hooks are still an experimental surface. The reliable core is the deterministic gate scripts plus review artifacts.
