---
name: karpathy-engineering
description: Use when writing, reviewing, or refactoring code to avoid hidden assumptions, overengineering, broad unrelated edits, and unverifiable success criteria.
---

# Karpathy Engineering

Use this skill for non-trivial engineering work before implementation and during review.

## Core Rules

1. Think before coding.
2. Prefer the simplest design that satisfies the request.
3. Make surgical changes only.
4. Convert the request into verifiable success criteria.

## Steps

1. State assumptions explicitly.
2. If multiple interpretations exist, name them and choose only when the choice is low-risk.
3. Push back when the simpler path is better.
4. Define the smallest implementation slice.
5. Define validation before editing.
6. Avoid speculative abstractions, generic frameworks, and unrelated cleanup.
7. After implementation, inspect the diff: every changed line should trace to the user request.

## Red Flags

- A one-off need became a reusable framework.
- New configuration exists without a current consumer.
- Adjacent code was reformatted or refactored without being required.
- The plan says "make it work" but has no deterministic validation.
- Tests were skipped without saying why.

## Output Contract

Return:

- assumptions
- simplest viable path
- rejected complexity
- owned paths
- validation criteria
- residual uncertainty

Do not slow down trivial one-line edits unless the user asks for rigor.
