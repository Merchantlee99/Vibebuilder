# Known Gaps

- This template is not initialized as a Git repository.
- Hooks are disabled by default in `.codex/config.toml`.
- Automations are described by policy but not scheduled from this template.
- CI is not configured because this directory is currently a local template, not a repository.
- `score.py` measures harness readiness, not empirical product quality.
- Normal reviews can opt into prepared-event nonce/fingerprint checks and HMAC approval. High-risk reviews require policy-backed HMAC approval by default, but true human identity still requires `HARNESS_REVIEW_SECRET` to be held outside the Codex session.
- Event log hash chains and segment manifests detect line tampering and many accidental truncations. They do not replace off-site backup, signed commits, or OS-level append-only file protection.
- `subagent_planner.py` records planned model policy, not the actual model selected by every Codex surface. Runtime model verification depends on Codex exposing that metadata.
- v5 simplicity, design, and evidence gates check artifacts and evidence shape, not full semantic code simplicity or actual visual taste.
- UI/UX quality still benefits from browser QA, screenshot review, accessibility tooling, and human design judgment.
- The upstream UI/UX Pro Max searchable database is not bundled; this template uses a lighter Codex-native workflow.
- High-risk HMAC approval only proves external approval when `HARNESS_REVIEW_SECRET` is held outside the Codex session.
