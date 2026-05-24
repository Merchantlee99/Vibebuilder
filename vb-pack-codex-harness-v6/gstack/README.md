# GStack Workflow Catalog

GStack is the v6 workflow catalog. It does not replace `AGENTS.md`, skills, or gates. It maps a natural-language request to the smallest useful operating stack:

- PM framing and acceptance criteria.
- Intent routing and required spec layers.
- Subagent roles and review ownership.
- Evidence gates that must prove completion.
- Strict review when the route touches high-risk surfaces.

Use GStack as routing guidance, not as a second constitution. If a workflow conflicts with `AGENTS.md`, `harness/runtime.json`, or `harness/strict_policy.json`, the stricter project policy wins.

## Workflows

- `workflows/intent-routed-implementation.md`: default normal+ coding path.
- `workflows/grill-with-docs-team-rules.md`: codebase-aware grilling and team-rule proposal path.
- `workflows/ui-evidence-review.md`: UI work with visual, layout, accessibility, and customer UX evidence.
- `workflows/high-risk-strict.md`: auth, billing, data deletion, security, migration, and irreversible work.
