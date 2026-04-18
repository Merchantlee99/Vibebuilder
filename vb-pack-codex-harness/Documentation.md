# Documentation.md — Codex Native Harness

## Status

Codex-native harness baseline is complete, verification is green, and the hardening pass for review independence, filesystem activity bridging, template-safe mode separation, structured subagent dispatch, and automation intent planning has been added.

## Decisions

- Use `.codex/` instead of `.claude/` as the control plane.
- Treat `subagents`, `worktree`, and `automations` as first-class operating primitives.
- Keep v0 scripts stdlib-only.
- Prefer playbooks and manifests over provider-specific hook wiring.
- Add explicit runtime gates instead of pretending undocumented hook integration exists.
- Add hermes-inspired feedback loop as `prefetch -> sync -> propose skill -> insights`.
- Add filesystem-driven activity sync so artifact changes can still land in telemetry without undocumented Codex app hooks.
- Require reviewer and producer metadata plus distinct sessions for `normal+` completion reviews.
- Keep template repositories pinned to `advisory` and allow `enforced` only after a copied project instance is explicitly adopted.
- Add an optional repo-local hook adapter on top of the official Codex hooks surface, but keep it disabled in template mode.
- Add planner scripts so subagent dispatch and automation follow-up become structured state, not just prose rules.

## Known Gaps

- There is still no direct Codex app-native hook bridge; telemetry sync happens when harness commands run
- Review gating now has dedicated `review_gate.py prepare/finalize` commands, but it still depends on operators invoking CLI gate steps
- The optional hook adapter depends on the user enabling `codex_hooks = true` in their Codex config
- Planner scripts can suggest subagent and automation structure, but actual subagent spawning and automation creation still depend on Codex app tool surfaces
- Proposed skills are drafts, not promoted skills
- Worktree flow still needs a real git-backed project and at least one commit before parallel worker execution
- Template adoption into a real project is still a CLI step, not an automatic first-run detection

## Restart Point

Run the harness checks:

```bash
python3 scripts/harness/self_test.py
python3 -m unittest discover -s tests -q
```

Verification is already green. Next step is to run the harness against a real task and tighten any rough edges found in practice.
