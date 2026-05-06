# Strict Operations

Use strict operations for high-risk work: auth, payments, secrets, destructive actions, data migrations, production infrastructure, compliance, and broad changes with ambiguous blast radius.

## Requirements

- High-risk work requires a task profile with `strict_required: true`.
- High-risk task profiles must include a strict gate in `required_gates`.
- Independent review is required.
- Prepared review events are required.
- HMAC approval support must remain available for high-risk review finalization.
- Rollback and residual risk must be explicit.

## Template Boundary

The default v5 template uses advisory mode. Projects can adopt stricter profiles through `harness/strict_policy.json` and runtime settings.
