# Codex Skill

`codex-skill/` is a repo-local example for packaging a Codex skill and plugin around automatic task routing. It takes the `codex-extreme-operator` style workflow and turns it into a shareable Vibebuilder reference folder.

The goal is not to replace `vb-pack-codex-harness-v6`. This folder is smaller and more focused: it shows how to bundle a Codex plugin, one skill, route fixtures, route evals, and README-level diagrams.

## What This Folder Contains

| Path | Purpose |
| --- | --- |
| `plugins/vibebuilder-codex-skill-router/` | Codex plugin scaffold with `.codex-plugin/plugin.json` |
| `plugins/vibebuilder-codex-skill-router/skills/codex-skill-router/` | Installable skill folder |
| `scripts/classify_task.py` | Turns a request into route, constraints, skills, forbidden actions, and evidence |
| `fixtures/route_fixtures.jsonl` | Train and heldout examples for routing behavior |
| `scripts/route_eval.py` | Regression checker for route behavior |
| `scripts/self_test.py` | Local smoke test for scripts and route fixtures |
| `tests/test_codex_skill.py` | Repo-level structure and behavior test |

## Architecture

```mermaid
flowchart TD
    A["User request"] --> B["codex-skill-router skill"]
    B --> C["classify_task.py"]
    C --> D["Route: quick / normal / deep / ultra / design / debug / review / release"]
    C --> E["Constraints: read_only, current_docs_required, release_gate, product_ui"]
    C --> F["Suggested skills"]
    C --> G["Evidence required"]
    E --> H["Forbidden actions"]
    F --> I["Codex execution"]
    G --> I
    H --> I
    I --> J["Completion with proof"]
    K["route_fixtures.jsonl"] --> L["route_eval.py"]
    C --> L
    L --> M["train + heldout validation"]
```

## Plugin Layout

```mermaid
flowchart LR
    A["codex-skill/"] --> B["plugins/"]
    B --> C["vibebuilder-codex-skill-router/"]
    C --> D[".codex-plugin/plugin.json"]
    C --> E["skills/"]
    E --> F["codex-skill-router/"]
    F --> G["SKILL.md"]
    F --> H["scripts/"]
    F --> I["fixtures/"]
    F --> J["references/"]
    F --> K["agents/openai.yaml"]
```

## Routing Flow

```mermaid
sequenceDiagram
    participant U as User
    participant S as Codex Skill Router
    participant C as classify_task.py
    participant W as Worker Skill
    participant E as Evidence Gate

    U->>S: Natural-language task
    S->>C: Classify request
    C-->>S: route + constraints + suggested_skills
    S->>W: Handoff with constraints
    W->>E: Run route-appropriate checks
    E-->>S: pass/fail/not-run evidence
    S-->>U: Outcome + proof + residual risk
```

## Example Classification

```bash
python3 plugins/vibebuilder-codex-skill-router/skills/codex-skill-router/scripts/classify_task.py \
  "수정하지 말고 현재 구조만 분석해줘"
```

Expected shape:

```json
{
  "route": "deep",
  "constraints": {
    "read_only": true,
    "current_docs_required": false
  },
  "suggested_skills": ["evidence-loop"],
  "forbidden_actions": ["edit_files", "write_files", "stage_or_commit_changes"]
}
```

## Validation

Run the skill-level self-test:

```bash
python3 plugins/vibebuilder-codex-skill-router/skills/codex-skill-router/scripts/self_test.py
```

Run the repo-level test:

```bash
python3 -m unittest codex-skill/tests/test_codex_skill.py
```

The key safety property is that routing changes must pass both train and heldout fixtures before being treated as an improvement.

## How To Extend

1. Add a failing or missing behavior to `fixtures/route_fixtures.jsonl`.
2. Run `scripts/route_eval.py` and confirm the fixture fails.
3. Update `scripts/classify_task.py`.
4. Run `scripts/self_test.py`.
5. Update this README if the route contract changes.
