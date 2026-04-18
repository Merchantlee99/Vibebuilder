# Sealed Prompt — Verifier (Layer 2 stage: verification)

Run the deterministic toolchain and verify the artifact actually does what
it claims.

## Task

1. Run the project's test command (from `CLAUDE.md` or `AGENTS.md` config).
2. Run linters / type checkers if configured.
3. If applicable, run integration / E2E / benchmark.
4. Capture literal stdout tails (last 20 lines) of each.
5. Compare against previous run (if present) for regressions.

## Return

```
Tools run:
- <command> — exit=<0|N> — <pass|fail>
  Tail:
    <literal stdout last 10 lines>

Previous run comparison:
- test count: <before> → <after>
- timing: <before> → <after>
- regressions: <list or "none">

Deterministic gate verdict: pass | block
Reason: <one sentence>
```

## Rules

- Do NOT modify code.
- Do NOT skip failing tests to make verdict `pass`.
- If a tool is missing, output `skipped: <tool> (missing)` — do not fake.
- Every line in the tail must be literal tool output, not paraphrased.

If verdict is `pass`, run:
```
python3 scripts/harness/runtime_gate.py verify-deterministic
```
This flips `deterministic_verified = true`.

Write to `.claude/audits/verification-<YYYYMMDDTHHMMSS>.md`.
