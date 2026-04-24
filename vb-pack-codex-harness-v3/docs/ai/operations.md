# Codex Harness v3 Operations

This harness is designed for natural-language use with strict/high-trust defaults. The user should not need to remember commands during normal work; Codex should choose the right gates.

## Natural-Language Requests

Use prompts like:

- "하네스 기준으로 이 기능을 설계하고 구현해줘."
- "중요한 기능이니 PM 기획, red team, 구현, 리뷰까지 진행해줘."
- "이 PR을 하네스 기준으로 리뷰해줘."
- "장기 작업이니 필요한 follow-up automation까지 제안해줘."

Codex should then decide whether to use:

- `pm_strategist` for product framing.
- `pm_redteam` for plan critique.
- `docs_researcher` for official documentation.
- `code_mapper` for code path exploration.
- `task_distributor` for parallel slicing.
- `worker` for bounded implementation.
- `reviewer` or `security_auditor` for independent review.
- Worktree mode for broad or risky implementation.
- Automations for waits, retros, stale review, or skill triage.

## Manual Commands For Maintainers

These commands exist so Codex and maintainers can verify the harness:

```bash
python3 scripts/harness/self_test.py
python3 scripts/harness/harness.py check --tier normal --template
python3 scripts/harness/score.py
python3 scripts/harness/gate.py all --tier normal --template
python3 scripts/harness/review_gate.py prepare --tier normal --producer main-codex
python3 scripts/harness/subagent_planner.py check
python3 scripts/harness/automation_planner.py audit
python3 scripts/harness/skillify_audit.py all
python3 scripts/harness/session_index.py rebuild
python3 scripts/harness/ops_metrics.py
python3 scripts/harness/event_log.py verify
python3 scripts/harness/event_log.py rotate --max-bytes 1048576
python3 scripts/harness/strict_gate.py --template
```

`score.py` is a readiness score, not proof of real-world output quality. Use `ops_metrics.py`, review findings, validation evidence, and CI history for operational quality.

## Project Adoption

For a copied real project:

```bash
python3 scripts/harness/adopt_project.py --check
python3 scripts/harness/adopt_project.py --write
```

Use `--enable-hooks` only after reviewing `.codex/hooks.json`, because hooks are optional and experimental.

For v3 strict adoption:

```bash
python3 scripts/harness/adopt_project.py --write --profile strict
python3 scripts/harness/strict_gate.py --profile strict
```

## Completion Contract

For `normal+` work, Codex should not claim completion until:

- plan exists and has validation and rollback
- implementation validation is recorded
- independent review is accepted or accepted with follow-up
- subagent ownership claims are released or intentionally left active
- automation follow-up is proposed when work spans time
- residual risks are stated
- strict gate is clean for strict/team/production profiles

## Observability

The harness writes append-only events under `harness/telemetry/events.jsonl` and learnings under `harness/telemetry/learnings.jsonl`.

Use:

```bash
python3 scripts/harness/event_log.py tail --log events
python3 scripts/harness/event_log.py verify
python3 scripts/harness/event_log.py rotate --force
python3 scripts/harness/session_index.py search "review"
python3 scripts/harness/ops_metrics.py
python3 scripts/harness/strict_gate.py
```

`events.jsonl` uses a SHA256 hash chain and `events.manifest.json` tracks rotated segments. Segment rotation improves forensic durability for older events, but it is not a replacement for external backup, git-based archival, or OS-level append-only file protection.

## High-Trust Review Approval

For sensitive work, require an external approval token during review finalize:

```bash
python3 scripts/harness/review_gate.py finalize \
  --review-file harness/reviews/review-YYYYMMDDTHHMMSSZ.md \
  --require-prepared-event \
  --hmac-secret-env HARNESS_REVIEW_SECRET \
  --approval-token <hmac-sha256(review_file:nonce)>
```

This is optional by design. It strengthens chain-of-trust when the secret is held outside the Codex session. If Codex has access to the secret, treat it as additional audit evidence, not proof of human identity.

In v3, high-risk HMAC approval is policy-required once `enforcement_mode` is `enforced`.

## Umbrella CLI

`scripts/harness/harness.py` wraps the main maintenance commands so maintainers do not need to remember every script path:

```bash
python3 scripts/harness/harness.py events verify
python3 scripts/harness/harness.py automation scan
python3 scripts/harness/harness.py learning --threshold 2 --json
python3 scripts/harness/harness.py subagent plan --role reviewer --owner reviewer --goal "review plan"
```
