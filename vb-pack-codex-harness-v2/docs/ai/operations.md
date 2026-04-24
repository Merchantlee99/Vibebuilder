# Codex Harness Operations

This harness is designed for natural-language use. The user should not need to remember commands during normal work.

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
python3 scripts/harness/score.py
python3 scripts/harness/gate.py all --tier normal --template
python3 scripts/harness/review_gate.py prepare --tier normal --producer main-codex
python3 scripts/harness/subagent_planner.py check
python3 scripts/harness/automation_planner.py audit
python3 scripts/harness/skillify_audit.py all
```

## Project Adoption

For a copied real project:

```bash
python3 scripts/harness/adopt_project.py --check
python3 scripts/harness/adopt_project.py --write
```

Use `--enable-hooks` only after reviewing `.codex/hooks.json`, because hooks are optional and experimental.

## Completion Contract

For `normal+` work, Codex should not claim completion until:

- plan exists and has validation and rollback
- implementation validation is recorded
- independent review is accepted or accepted with follow-up
- subagent ownership claims are released or intentionally left active
- automation follow-up is proposed when work spans time
- residual risks are stated

