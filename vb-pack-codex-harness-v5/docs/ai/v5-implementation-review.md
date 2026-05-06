# v5 Implementation Review

## Scope

Implemented the v5 blueprint as a working harness pack, not only a design document.

The implementation starts from the v4 backbone and adds v5-specific task profiling, evidence logging, UI evidence gates, runtime/non-web UI gates, static frontend audit, benchmark guardrails, Hermes-style memory curation, new subagent roles, new skills, templates, and tests.

## Implemented Files

Core policy:

- `AGENTS.md`
- `README.md`
- `harness/runtime.json`
- `harness/evidence/evidence-matrix.json`
- `harness/visual/README.md`
- `harness/memory/README.md`
- `harness/evals/README.md`

New agents:

- `.codex/agents/browser-qa.toml`
- `.codex/agents/visual-reviewer.toml`
- `.codex/agents/learning-curator.toml`

New skills:

- `.agents/skills/implementation-evidence/SKILL.md`
- `.agents/skills/ui-evidence/SKILL.md`
- `.agents/skills/browser-qa/SKILL.md`
- `.agents/skills/visual-review/SKILL.md`
- `.agents/skills/accessibility-audit/SKILL.md`
- `.agents/skills/eval-loop/SKILL.md`
- `.agents/skills/memory-curation/SKILL.md`

New scripts:

- `scripts/harness/evidence_log.py`
- `scripts/harness/task_profile_gate.py`
- `scripts/harness/implementation_gate.py`
- `scripts/harness/ui_evidence_gate.py`
- `scripts/harness/runtime_evidence_gate.py`
- `scripts/harness/non_web_ui_evidence_gate.py`
- `scripts/harness/strict_gate.py`
- `scripts/harness/memory_guard.py`
- `scripts/harness/frontend_static_audit.py`
- `scripts/harness/benchmark_harness.py`

New templates:

- `templates/Task-Profile.json`
- `templates/Visual-Evidence.md`
- `templates/Memory-Proposal.md`
- `templates/Strict-Adoption.md`

Updated integration points:

- `scripts/harness/gate.py`
- `scripts/harness/harness.py`
- `scripts/harness/self_test.py`
- `scripts/harness/score.py`
- `tests/test_harness.py`
- `harness/model_policy.json`
- `.gitignore`

## Design Intent Check

| Blueprint intent | Implementation status |
| --- | --- |
| Preserve v2/v3/v4 coding baseline | v4 copied as backbone; existing quality, review, simplicity, design, risk, subagent, automation, event, score, session gates retained |
| Add task-profile routing without script overreach | `task_profile_gate.py` validates profile shape and objective misclassification only |
| Scripts validate evidence, not taste | Evidence gates check presence, shape, artifact paths, route/state/viewport, and screenshot-only violations |
| Normal+ implementation needs proof | `implementation_gate.py` requires a task id, implementation artifact, and passing command evidence |
| UI cannot pass on screenshot alone | `ui_evidence_gate.py` rejects normal+ required UI evidence unless a non-screenshot record exists |
| CSS/frontend code can be inspected | `frontend_static_audit.py` inventories raw colors, arbitrary Tailwind values, token class patterns, and layout-risk hints |
| Runtime and non-web UI are separate paths | `runtime_evidence_gate.py` and `non_web_ui_evidence_gate.py` added |
| v3 high-risk strictness is preserved | `strict_gate.py`, `strict_policy.json`, strict operations docs, and strict adoption template added |
| Hermes-style learning is quarantined | `memory_guard.py` requires source id, repeated count, confidence, review date, test fixture, reviewer verdict, and explicit approval for direct promote |
| v5 overhead is measured | `benchmark_harness.py` compares compatible checks against v4 |

## v2/v3/v4/v5 Side-By-Side

| Harness | Script count | Distinct capability |
| --- | ---: | --- |
| v2 | 19 | implementation discipline, review, subagent planning, quality, event/session state |
| v3 | 20 | v2 plus strict high-risk gate |
| v4 | 21 | v2 plus simplicity and UI/UX artifact gate |
| v5 | 31 | v4 plus task profile, evidence log, implementation evidence, strict gate, UI runtime evidence, non-web UI, frontend static audit, memory guard, benchmark |

What is visibly different in v5:

- New `harness/evidence/`, `harness/visual/`, `harness/memory/`, and `harness/evals/` state areas.
- New `browser_qa`, `visual_reviewer`, and `learning_curator` roles.
- New evidence-oriented skills instead of only design-oriented instructions.
- New scripts that can prove the UI gate rejects screenshot-only normal work.
- New benchmark path that compares v5 overhead against v4-compatible commands.

## Verification Run

Commands run:

```bash
python3 scripts/harness/self_test.py
python3 -m unittest discover -s tests -q
python3 scripts/harness/score.py --min-score 95 --json
python3 scripts/harness/benchmark_harness.py --quick --baseline-root ../vb-pack-codex-harness-v4 --output /tmp/v5-benchmark-final.json --json
```

Results:

- `self_test.py`: pass
- unittest: 34 tests, pass
- score: 100/100, pass
- benchmark: pass
- v5 trivial gate vs v4: +14.58ms in the latest run
- v5 normal template gate vs v4: +8.44ms in the latest run
- v5 quality template vs v4: +6.59ms in the latest run
- benchmark warnings: none

## Issues Found And Fixed

- During validation, `evidence_log.py append --command ...` collided with the argparse subcommand destination and fell through to an assertion. Fixed by separating the evidence command text destination from the subcommand name.
- Final review found that v5 evidence gates were opt-in. Fixed by wiring task profile, implementation, UI, runtime, non-web UI, and strict gates into `gate.py all`.
- Final review found that v3 strictness was claimed but missing. Fixed by adding v5 strict policy, strict gate, strict operations docs, and strict adoption template.
- Final review found that bootstrap recreated v4 defaults. Fixed by updating bootstrap defaults and directories to v5.
- Final review found sensitive UI policy was warning-only. Fixed by making unredacted sensitive visual evidence a blocker and adding `redacted` / `no_screenshot_reason` evidence fields.
- Final review found high-risk profiles could omit strict gates. Fixed by making missing strict gate an error in `task_profile_gate.py`.
- Final review found high-risk HMAC was only enforced when the caller passed `--hmac-secret-env`. Fixed by making high-risk finalize default to the policy-defined `HARNESS_REVIEW_SECRET` environment variable.
- Final review found the umbrella `harness.py check` could not pass non-default artifact or review locations. Fixed by forwarding `--artifact-dir` and `--review-file` to `gate.py all`.
- Final review found v4-era shared docs and docstrings. Fixed by refreshing user-facing docs and harness package docstrings to describe v5.

## Residual Risk

- Browser screenshot capture is not implemented as a built-in Playwright adapter yet. v5 validates evidence once captured, and the blueprint leaves Playwright/axe adapters as the next implementation slice.
- Static frontend audit is intentionally heuristic. It catches token drift hints and arbitrary values, not actual computed layout.
- `implementation_gate.py` is evidence-shape focused. It does not decide whether a test suite is semantically sufficient.
- v5 is advisory as a template. A project adoption step must choose which gates become enforced.

## Final Judgment

The implemented v5 is materially different from v2/v3/v4. It is no longer only a rule/artifact harness. It now has an executable evidence layer that can reject missing implementation proof, reject screenshot-only UI completion, validate task profile misclassification, quarantine self-improvement, and benchmark overhead against v4.
