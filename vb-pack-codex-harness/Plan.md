# Plan.md — Codex Native Harness

## Milestones

### M1: Governance and policy skeleton

- Goal: establish the operating contract for Codex-native work
- In scope: `AGENTS.md`, `README.md`, `ETHOS.md`, `.codex/manifests/**`, `.codex/playbooks/**`
- Out of scope: advanced automation helpers
- Validation: self-test checks file presence and JSON validity
- Done-when: core docs and manifests exist with coherent routing rules

### M2: Templates and scripts

- Goal: make the harness executable as a reusable repo skeleton
- In scope: `templates/**`, `scripts/harness/**`, `tests/**`
- Out of scope: app-specific integrations beyond docs and stdlib scripts
- Validation: `python3 scripts/harness/self_test.py`, `python3 -m unittest discover -s tests -q`
- Done-when: bootstrap/logging/audit scripts and baseline tests are in place

### M3: Seeded sample docs

- Goal: ensure the repo explains its own current state and restart path
- In scope: root `Prompt.md`, `PRD.md`, `Plan.md`, `Implement.md`, `Documentation.md`, `Subagent-Manifest.md`
- Out of scope: downstream project customization
- Validation: manual review and self-test
- Done-when: a fresh session can resume from these files alone

## Ordered Slices

| # | Slice | Owner | Paths | Validation |
|---|-------|-------|-------|------------|
| 1 | Core docs and manifests | main | root docs, `.codex/manifests`, `.codex/playbooks` | self-test presence |
| 2 | Templates and scripts | main | `templates`, `scripts/harness`, `tests` | self-test + unittest |
| 3 | Seeded project docs | main | root docs, `.codex/context` | manual consistency check |

## Rollback

- If M1 fails: revert doc/manifests patch as one logical change
- If M2 fails: disable script usage and keep docs-only skeleton until fixed
- If M3 fails: reseed root docs from templates and update restart point

## Tier

- tier: high-risk
- complexity: complex
- reason: this repo defines an operating framework, touches governance, scripts, and long-term project behavior
