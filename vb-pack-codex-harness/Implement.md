# Implement.md — Codex Native Harness

## Current Slice

- Slice: harden subagent dispatch and automation continuity for Codex-native long-running work
- Owner: main Codex session
- Mode: local
- Write scope: root docs, `.codex/**`, `templates/**`, `scripts/harness/**`, `tests/**`

## Commands

```bash
mkdir -p .codex/manifests .codex/context .codex/reviews .codex/audits .codex/playbooks .codex/telemetry templates scripts/harness tests
python3 scripts/harness/subagent_planner.py plan --role worker --owner worker-sample --goal "sample slice" --write-scope src/sample --claim
python3 scripts/harness/automation_planner.py scan
python3 scripts/harness/self_test.py
python3 -m unittest discover -s tests -q
```

## Findings

- Codex-native harness benefits more from mode and subagent policy than Claude-style hook enforcement.
- stdlib-only scripts keep the template portable.
- runtime/review enforcement has to be explicit because Codex app does not expose the same hook model as Claude Code.
- hermes-inspired durability fits best as a feedback loop layer rather than a hard gate layer.
- subagent guidance becomes much more actionable once dispatch specs and ownership claims are generated as structured state.
- automation guidance becomes materially better once pending review and evolution loops are emitted as concrete suggestions instead of prose only.

## Validation

- `python3 scripts/harness/bootstrap.py` passed
- `python3 scripts/harness/subagent_planner.py plan --role worker --owner worker-sample --goal "sample slice" --write-scope src/sample --claim` passed
- `python3 scripts/harness/automation_planner.py scan` passed
- `python3 scripts/harness/self_test.py` passed
- `python3 -m unittest discover -s tests -q` passed
- `python3 scripts/harness/validate_manifests.py` passed

## Next

- Use the harness on the first real feature or repo migration
- Promote the first real pending-review or evolution-sweep suggestion into a Codex heartbeat automation
- Tighten planner heuristics after observing the first real parallel worker run
