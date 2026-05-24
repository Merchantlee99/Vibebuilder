# Grill With Docs And Team Rules

## Use When

Use when the repository already contains docs, tests, reviews, naming patterns, architecture decisions, or repeated team conventions.

## Stack

- Code mapper: inspect existing docs, tests, and local conventions.
- PM redteam: grill the request against existing product intent and edge cases.
- Router: set `needs_grill_with_docs=true` and `codebase_context=true`.
- Team-rule miner: draft `harness/team/rule-proposals/*.md` only when the pattern is repeated and evidence-backed.
- Reviewer: decide whether a proposed rule stays proposed, is rejected, or is approved for narrow promotion.

## Required Gates

`intent_router_gate`, `team_rule_mining_gate`, and `rule_promotion_gate` if promotion is requested.

## Stop Condition

Do not auto-promote rules into `AGENTS.md`, `.codex/config.toml`, hooks, or strict policy without explicit reviewer approval and an override gate.
