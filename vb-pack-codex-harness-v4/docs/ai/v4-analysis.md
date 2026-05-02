# v4 Analysis

## Creation Intent

Codex Harness v4 exists to make the daily v2 harness better for product-building work where both engineering restraint and UI/UX quality matter.

The template is designed to reduce two common failure modes:

- Engineering drift: hidden assumptions, speculative abstractions, broad unrelated edits, weak validation.
- Design drift: generic UI, missing design system, weak accessibility, untested responsive and interaction states.

v4 is not a replacement for v3 strict/high-trust operations. Use v3 for production security, payments, audit-heavy work, or team enforcement. Use v4 when the main risk is "Codex builds too much" or "Codex builds a mediocre interface."

## Reference Mapping

From `forrestchang/andrej-karpathy-skills`, v4 adopts:

- Think before coding.
- Simplicity first.
- Surgical changes.
- Goal-driven execution.

From `nextlevelbuilder/ui-ux-pro-max-skill`, v4 adopts:

- UI/UX skill activation for natural-language UI tasks.
- Design-system-first workflow.
- Accessibility, interaction, responsive, typography/color, motion, performance checks.
- Pre-delivery UI anti-pattern review.

The full upstream UI/UX search database is not embedded. v4 only includes a lightweight Codex-native workflow and gate layer.

## Does It Work As Intended?

At template level, yes if these checks pass:

- `python3 scripts/harness/self_test.py`
- `python3 -m unittest discover -s tests -q`
- `python3 scripts/harness/score.py --min-score 95`
- `python3 scripts/harness/simplicity_gate.py --template`
- `python3 scripts/harness/design_gate.py --template`

At project level, measure whether:

- Plans state assumptions and validation criteria before edits.
- Diffs are smaller and do not include drive-by refactors.
- UI work produces design-system artifacts before implementation.
- UI review catches accessibility, responsive, interaction-state, and visual consistency issues.
- Repeated UI or simplicity failures become proposed skills rather than repeated manual reminders.

## Weaknesses

- Skill routing is advisory. Codex can still fail to load `karpathy-engineering` or `ui-ux-design`.
- Gates inspect artifacts and language, not the full semantic quality of code or visual design.
- UI quality still needs browser inspection, screenshots, or human taste review.
- The UI reference is lighter than the upstream UI/UX Pro Max database.
- More artifacts can slow tiny tasks if Codex over-applies the workflow.
- v4 does not add v3's strict HMAC or production branch protection controls.

## Weakness Mitigation

- Keep `karpathy-engineering` optional for trivial work.
- Require `Simplicity-Review.md` only for broad or ambiguous changes.
- Require UI artifacts only when `design_gate.py --ui` or UI context is detected.
- Use browser QA for frontend work whenever available.
- Add screenshot evidence to `UI-Review.md` for visual regressions.
- Promote repeated project-specific design patterns through `skillify-proposal`.
- Use v3 instead of v4 when the risk is security, money, data integrity, or team enforcement.

## Better Additional Resources

- OpenAI Codex use cases for frontend design, PR review, skills, automations, long-horizon tasks.
- WCAG for accessibility.
- Apple Human Interface Guidelines for mobile/platform interaction quality.
- Material Design for layout, motion, state, and component guidance.
- Storybook for component inventory and visual review.
- Playwright or browser QA for deterministic frontend regression checks.
- Refactoring by Martin Fowler for safe restructuring.
- A Philosophy of Software Design by John Ousterhout for complexity control.
