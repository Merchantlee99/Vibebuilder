# Current Focus

## Active Goal

Use the first usable Codex-only harness baseline in this repository and iterate toward v1.

## Immediate Priorities

1. Apply the harness to a real project task
2. Decide whether to add automatic worktree bootstrap helpers
3. Observe whether operators actually use `runtime_gate.py` and `ownership_guard.py`
4. Promote or discard proposed skills based on real telemetry

## Restart Point

Run:

```bash
python3 scripts/harness/self_test.py
python3 -m unittest discover -s tests -q
```

Then continue by opening a real task with `Prompt.md` and revising `Subagent-Manifest.md` for the first non-trivial implementation.
