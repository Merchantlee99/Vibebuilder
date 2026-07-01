# Plugin Adoption

This plugin is intentionally small. It demonstrates the minimum shape needed to package a Codex skill router:

```text
vibebuilder-codex-skill-router/
├── .codex-plugin/plugin.json
└── skills/
    └── codex-skill-router/
        ├── SKILL.md
        ├── agents/openai.yaml
        ├── fixtures/route_fixtures.jsonl
        ├── references/
        └── scripts/
```

## Use In A Vibebuilder Pack

Use this package when:

- natural-language requests should be classified before work starts.
- read-only requests should suppress implementation automatically.
- release, debug, review, design, and current-docs work need different evidence.
- skill or routing improvements need train and heldout evals.

Do not use it as the only production safety layer. It is a routing and evidence contract, not a replacement for project-specific tests, security review, or release policy.

## Extension Points

- Add route fixtures for repeated user corrections.
- Add route-specific skills under `skills/`.
- Add stronger evals when a route controls production or destructive behavior.
- Add a repo marketplace entry only when the repo explicitly wants plugin installation metadata.
