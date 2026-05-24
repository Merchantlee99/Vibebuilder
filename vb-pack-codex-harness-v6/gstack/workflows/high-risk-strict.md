# High-Risk Strict Workflow

## Use When

Use for auth, permissions, billing, payment, secrets, privacy, destructive actions, migrations, data deletion, security, public API changes, and irreversible user impact.

## Stack

- Risk classifier: classify the route as `high-risk`.
- PM strategist: document authority, rollback, failure modes, and acceptance criteria.
- Security auditor: review attack paths and policy implications.
- Strict gate: require strict profile checks and high-risk review policy.
- Reviewer: finalize only with HMAC approval when configured by policy.

## Required Gates

`intent_router_gate`, `strict_gate`, `implementation_gate`, `review_gate`, and any route-selected spec or runtime gates.

## Stop Condition

Do not downgrade high-risk work to normal to reduce overhead. Split safe sub-slices only when each slice has independent rollback and evidence.
