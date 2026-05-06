---
name: eval-loop
description: Use when changing harness gates, routing rules, skills, or automation behavior and benchmark/eval evidence is needed to avoid slowing normal coding performance. Do not use for ordinary app code changes.
---

# Eval Loop

## Steps

1. Identify the harness behavior being changed.
2. Run existing self-test and score checks.
3. Run quick benchmark tasks.
4. Compare overhead against v4 or the previous baseline when available.
5. Record whether added checks caught real risk.

## Output Contract

Return benchmark commands, elapsed time, failures, false-positive risk, and promotion recommendation.
