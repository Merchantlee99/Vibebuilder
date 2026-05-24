---
name: domain-language
description: Use when work introduces or changes shared nouns, states, IDs, ownership, authority, or customer-facing vocabulary.
---

# Domain Language

Use this skill to create or update `Domain-Language.md`.

## Steps

1. Identify canonical terms, rejected aliases, entities, states, ownership, and invariants.
2. Check nearby code, tests, docs, and UI copy for existing usage.
3. Record ambiguous terms as open questions instead of guessing.
4. Run `scripts/harness/domain_language_gate.py`.

## Output Contract

Return the domain language artifact path, canonical terms, rejected aliases, and unresolved decision gaps.
