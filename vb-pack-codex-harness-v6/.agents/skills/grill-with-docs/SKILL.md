---
name: grill-with-docs
description: Use when a codebase, docs, ADRs, tests, prior reviews, or team traces exist; align new work with existing shared language before implementation.
---

# Grill With Docs

Use this skill when the task touches an existing codebase or team context.

## Steps

1. Inspect `spec/`, `docs/ai/`, ADRs, README, tests, and nearby code for existing language and decisions.
2. Challenge fuzzy or conflicting terms against existing domain language.
3. Ask only questions that cannot be answered from project artifacts.
4. Update `Domain-Language.md`, `Feature-Spec.md`, or ADR candidates when shared language changes.
5. If repeated team conventions are discovered, create a team-rule proposal instead of changing always rules directly.

## Output Contract

Return the existing sources consulted, language conflicts found, proposed terms, and any spec or team-rule proposal created.
