# Known Gaps

- This template is not initialized as a Git repository.
- Hooks are disabled by default in `.codex/config.toml`.
- Automations are described by policy but not scheduled from this template.
- CI is not configured because this directory is currently a local template, not a repository.
- `score.py` measures harness readiness, not empirical product quality.
- Review identity can be strengthened with prepared-event nonce/fingerprint checks and optional HMAC approval, but true human identity still requires the secret to be held outside the Codex session.
- Event log hash chains and segment manifests detect line tampering and many accidental truncations. They do not replace off-site backup, signed commits, or OS-level append-only file protection.
- `subagent_planner.py` records planned model policy, not the actual model selected by every Codex surface. Runtime model verification depends on Codex exposing that metadata.
- v3 strict profile documents branch protection and off-site backup policy, but GitHub branch rules and external storage must be configured outside this template.
- Hooks are enabled in `.codex/config.toml`, but Stop hook blocking still depends on `harness/runtime.json` using `enforcement_mode = enforced`.
