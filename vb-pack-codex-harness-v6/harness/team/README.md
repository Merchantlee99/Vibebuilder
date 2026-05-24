# Team Rule Mining

v6 may infer team conventions from existing code, docs, tests, reviews, and PR traces.

Inference never equals promotion. Proposed rules must be written under:

```text
harness/team/rule-proposals/
```

and pass `team_rule_mining_gate.py` and `rule_promotion_gate.py` before becoming active skills, specs, or always rules.
