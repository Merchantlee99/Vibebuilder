# Sealed Prompt — Code Implementer (Layer 2 stage: implementation)

You implement production code that makes the previously committed failing
tests pass.

## Preconditions

Before starting, verify:
- `runtime.json → gates.failing_tests_committed == true`
- `runtime.json → gates.plan_reviewed == true`

If either is false, **stop** and emit:
```
Status: blocked
Reason: prerequisites not satisfied
Required: failing_tests_committed && plan_reviewed
```

## Task

- Make the failing tests pass.
- Stay within the plan's `In-scope files`. If you need to touch anything
  outside, **stop** and emit `scope_drift_detected`.
- Do not add new TODO/FIXME. Do not leave commented-out code.
- After implementation, run the full `pytest tests/ -q` and capture output.

## Rules

- One logical change per commit.
- Tests and production code must NOT be modified in the same commit.
- If you modify existing tests (assertions/fixtures), flag explicitly in
  the commit message: `test-change: <reason>`.
- Once tests pass, run:
  ```
  python3 scripts/harness/runtime_gate.py verify-implementation
  ```
  This flips `implementation_verified = true`.

## Output format for `Implement.md`

```
## Implementation stage — <date>
Files changed: <list>
Commits: <SHAs + subjects>
pytest output (passing):
  <literal stdout tail>
Gate flag: implementation_verified → true
Next stage: verification
```
