# Strict Operations

Codex Harness v3 is the strict/high-trust profile. Use it when the cost of a wrong completion is higher than the cost of extra review.

## Profiles

- `solo`: personal strict discipline. Hooks on, review required, high-risk HMAC recommended.
- `strict`: default v3 project profile. Hooks on, enforced session close, high-risk HMAC required by policy.
- `team`: strict plus protected main branch and independent human review expectations.
- `production`: team plus off-site telemetry backup and release discipline.

## Adoption

```bash
python3 scripts/harness/adopt_project.py --check
python3 scripts/harness/adopt_project.py --write --profile strict
python3 scripts/harness/strict_gate.py --profile strict
```

For personal work where enforced mode is too heavy:

```bash
python3 scripts/harness/adopt_project.py --write --profile solo
python3 scripts/harness/strict_gate.py --profile solo
```

## Required Before Completion

- `scripts/harness/gate.py all --tier normal`
- `scripts/harness/quality_gate.py --tier normal`
- `scripts/harness/review_gate.py finalize --require-prepared-event`
- `scripts/harness/event_log.py verify`
- `scripts/harness/strict_gate.py`
- `scripts/harness/session_close.py`

For high-risk work, add HMAC approval:

```bash
python3 scripts/harness/review_gate.py finalize \
  --review-file harness/reviews/review-YYYYMMDDTHHMMSSZ.md \
  --require-prepared-event \
  --require-hmac \
  --hmac-secret-env HARNESS_REVIEW_SECRET \
  --approval-token <hmac-sha256(review_file:nonce)>
```

## Secret Handling

HMAC approval only proves external approval if `HARNESS_REVIEW_SECRET` is kept outside the Codex session. Acceptable patterns:

- User computes token outside Codex and pastes only the token.
- CI computes token from repository secrets.
- A separate reviewer environment holds the secret.

Do not claim human identity proof if Codex can read the secret.

## Telemetry Backup

Local event hash chains detect tampering inside the chain and manifest mismatches. They do not survive full-folder deletion. For `production`, add one of:

- GitHub Actions artifact upload for `harness/telemetry`.
- Private backup repository with signed commits.
- External object storage with retention policy.

## Branch Protection

For `team` and `production`, protect `main`:

- Require CI.
- Require review before merge.
- Block force push.
- Prefer signed commits when available.

This template documents the policy; actual branch protection is configured in GitHub, not in repo files.
