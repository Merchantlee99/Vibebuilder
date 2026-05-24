---
name: req-evidence
description: Use before claiming normal+ completion when accepted REQ statements must be mapped to executed tests, guardrails, smoke checks, runtime/UI evidence, or named manual review.
---

# REQ Evidence

Use this skill to maintain `Req-Evidence-Map.md`.

## Steps

1. List every touched `REQ-...:Sx` statement.
2. Map each statement to evidence type, target, and execution record.
3. Keep generated stubs separate from executed evidence.
4. Run `scripts/harness/req_evidence_gate.py`.

## Output Contract

Return verified statements, manual-only statements, blocked statements, and missing evidence.
