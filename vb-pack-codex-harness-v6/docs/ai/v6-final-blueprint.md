# v6 Final Blueprint

## Position

Codex Harness v6 is an intent-routed spec and evidence harness.

v5 made completion evidence stronger. v6 adds the missing front half: natural-language intent routing, shared language, spec authority, REQ-to-evidence mapping, and reviewed team-rule mining.

## Architecture

```text
08_codex_harness_v6/
  AGENTS.md
  .agents/skills/
    intent-routing/
    grill-me/
    grill-with-docs/
    domain-language/
    spec-authoring/
    req-evidence/
    team-rule-mining/
  spec/
    00_constitution.md
    features/
    reviews/
    changes/
  templates/
    Intent-Routing.json
    Domain-Language.md
    Feature-Spec.md
    ADR.md
    Req-Evidence-Map.md
    Team-Rule-Proposal.md
    Spec-Review.md
  scripts/harness/
    intent_router_gate.py
    domain_language_gate.py
    spec_gate.py
    req_evidence_gate.py
    team_rule_mining_gate.py
    rule_promotion_gate.py
    spec_drift_gate.py
```

## Routing Rule

The user should not need to name gates. Codex routes the task, but the route is not trusted until `intent_router_gate.py` validates `Intent-Routing.json`.

## Completion Contract

Normal+ completion requires:

1. Intent route artifact.
2. Domain language when shared terms change.
3. L2 behavior spec when behavior changes.
4. L3 interface contract when rollback, idempotency, partial failure, payment, auth, deletion, or external integration matters.
5. REQ evidence map for accepted statements.
6. v5 implementation/UI/runtime/strict evidence as routed.
7. Independent review.
8. Team-rule proposals remain proposals unless promotion gates pass.

## Guardrail

AI can infer team conventions. AI cannot silently promote them.
