---
name: team-rule-mining
description: Use when existing codebase, docs, tests, reviews, or PR traces reveal repeated team conventions that might become reviewed rules.
---

# Team Rule Mining

Use this skill to propose conventions, not to silently activate them.

## Steps

1. Collect repeated patterns from code, tests, docs, reviews, PR templates, and existing rules.
2. Require multiple evidence points unless the user explicitly approves the rule.
3. Write `Team-Rule-Proposal.md` under `harness/team/rule-proposals/`.
4. Run `team_rule_mining_gate.py` and `rule_promotion_gate.py`.

## Output Contract

Return proposed rule, evidence, scope, collision check, risk, and promotion status. Do not edit `AGENTS.md` or active team rules without review.
