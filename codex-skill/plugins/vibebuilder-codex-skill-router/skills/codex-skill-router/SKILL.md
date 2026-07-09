---
name: codex-skill-router
description: Explicit GPT-5.6 native-first router for auditing, designing, installing, or validating Codex skill combinations, global skill setup, routing fixtures, and harness behavior. Use when the user explicitly invokes $codex-skill-router or asks to change or inspect Codex skills, routing, AGENTS guidance, or global harness configuration. Do not use for ordinary coding, review, debugging, research, or UI work merely because the task is complex.
---

# GPT-5.6 Codex Skill Router

Prefer GPT-5.6's native intent handling for ordinary work. Use this skill only to inspect or change the skill harness itself.

## Workflow

1. Run `scripts/classify_task.py "<request>"` for a deterministic first-pass contract.
2. Preserve `constraints` and `forbidden_actions`; treat `suggested_skills` as the smallest sufficient specialist set.
3. Interpret `reasoning_effort_hint` as a configuration hint. Do not add “think harder” or similar prompt text.
4. Satisfy `evidence_required` before making a completion claim.
5. When routing changes, update fixtures and run both train and held-out evals.

## Composition Rules

- Keep quick answers, small edits, prose changes, and routine code work native-first with no meta-skill stack.
- Use `openai-docs` for current OpenAI, GPT, ChatGPT, or Codex claims.
- Use `harness-doctor` for skill and routing changes.
- Use `debug-root-cause`, `review-swarm`, `deep-research-swarm`, `tdd-implementation`, or `visual-qa` only when their narrow trigger matches.
- Use `lazyweb-design` only for substantial product-UI discovery, critique, or redesign.
- Add `evidence-loop` for release gates, behavior fixes, or product-complete claims, not every edit.
- Add `git-checkpoint` only when the user explicitly authorizes a remote publish flow.

## Global Installation

Run `scripts/install_global.py` only when the user explicitly asks to change global Codex behavior. It:

- installs this skill to `$HOME/.agents/skills/codex-skill-router`;
- replaces broad global routing blocks with a compact GPT-5.6 contract;
- sets default reasoning effort to `high`;
- backs up and archives the legacy `apex`, `codex-extreme-operator`, and `design-impact-router` entry points outside active discovery, while retaining disabled config entries;
- migrates stale `network_access`, `child_agents_md`, `plugin_hooks`, and `codex_hooks` config keys for the current App CLI;
- creates a timestamped backup before writing.

Use `--dry-run` before installation when the target environment is unfamiliar.

## Validation

```bash
python3 scripts/route_eval.py --suite train
python3 scripts/route_eval.py --suite heldout
python3 scripts/self_test.py
```

Read `references/routing-contract.md` for the output schema and `references/plugin-adoption.md` for installation and rollback details.
