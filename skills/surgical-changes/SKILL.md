---
name: surgical-changes
description: Touch only what you must. Clean up only your own mess. Every changed line must trace directly to the user's request. Loaded by backend, frontend, ui, db, api agents as an always-load.
---

# Surgical Changes

**Touch only what you must. Clean up only your own mess.**

## The test
Before submitting any file change, ask: "Does every changed line trace directly to the user's request?"

If a line cannot be justified by the task → revert it.

## When editing existing code

- Do not "improve" adjacent code, comments, or formatting
- Do not refactor things that aren't broken
- Do not add docstrings, type hints, or logging that wasn't asked for
- Do not change code style or formatting — match what's already there, even if you'd do it differently
- Do not rename variables or methods outside the scope of the task
- If you notice unrelated dead code or a bug → **mention it, don't fix it**:
  > "I noticed [X] while working on this — it looks like it might be [issue]. Want me to address it separately?"

## When your changes create orphans

You **must** clean up what your changes made unused:
- Imports you made redundant
- Variables only used by code you deleted
- Functions only called by code you removed

You must **not** remove pre-existing dead code unless explicitly asked.

## Scope check before writing

Before calling `write` or `edit`, answer these:
1. What exactly did the user ask for?
2. Which files and lines does that actually require changing?
3. Is there anything else in my plan that goes beyond that?

If yes to (3) → remove it.

## Relationship to `atomic-changes`

`atomic-changes` governs PR scope — whether the PR is the right size.
`surgical-changes` governs file scope — whether each file edit is the right size.

Both apply. A perfectly atomic PR can still fail the surgical test if individual files were over-edited.