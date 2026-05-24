# Routing Operations

v6 is natural-language first. The user describes the outcome, and Codex records the route.

## Active Artifacts

For normal+ work, use:

- `docs/ai/current/Intent-Routing.json`
- `docs/ai/current/Task-Profile.json`
- `docs/ai/current/Domain-Language.md` when shared terms change
- `docs/ai/current/Feature-Spec.md` when behavior changes
- `docs/ai/current/Req-Evidence-Map.md` when accepted REQ statements are touched
- `docs/ai/current/Spec-Review.md` when doing reverse spec/code review

## Commands

```bash
python3 scripts/harness/harness.py intent-routing --template --json
python3 scripts/harness/harness.py domain-language --template --json
python3 scripts/harness/harness.py spec --template --json
python3 scripts/harness/harness.py req-evidence --template --json
python3 scripts/harness/harness.py team-rule --template --json
python3 scripts/harness/harness.py rule-promotion --template --json
python3 scripts/harness/harness.py spec-drift --template --json
```

## Team Rule Rule

Repeated project behavior may become a team-rule proposal. It cannot become an active always rule until evidence, collision review, test fixture, and reviewer approval are present.
