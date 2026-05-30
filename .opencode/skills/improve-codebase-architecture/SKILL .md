---
name: improve-codebase-architecture
description: Find deepening opportunities in the codebase — refactors that turn shallow modules into deep ones. Run every few days or after a surge of development. The aim is testability and AI-navigability. Loaded by architect when triggered explicitly by the developer.
---

# Improve Codebase Architecture

Run this after a surge of development, or every few days. Agent output quality is directly tied to codebase quality. A well-structured codebase produces better agent output. A ball of mud produces more mud.

## Core vocabulary (use these terms exactly)

**Module** — anything with an interface and an implementation: function, class, package, slice.
**Interface** — everything a caller must know to use the module: types, invariants, error modes, ordering, config. Not just the type signature.
**Deep module** — small interface, large implementation. The best kind. Hides complexity behind a clean surface.
**Shallow module** — interface nearly as complex as the implementation. Adds cognitive overhead without hiding complexity.
**Seam** — the boundary between two modules. Where you can change one side without touching the other.

Do not drift into "component", "service", "API", "boundary". Use the vocabulary above consistently.

## How to run

### 1. Orient first

Before exploring, run `zoom-out` on the repo. This produces an orientation map — entry points, module boundaries, domain vocabulary — that makes the exploration walk in Step 2 faster and more targeted. If `CONTEXT.md` exists, read it now.

### 2. Explore organically

Walk the codebase without a rigid checklist. Note where you experience friction:

- Where does understanding one concept require bouncing between many small modules?
- Where are modules shallow — interface nearly as complex as the implementation?
- Where have pure functions been extracted just for testability, but the real bugs hide in how they're called?
- Where do tightly-coupled modules leak across their seams?
- Which parts are untested or hard to test through their current interface?

Apply the **deletion test** to anything you suspect is shallow: would deleting this module concentrate complexity somewhere, or just move it? A "yes, it concentrates" is the signal you want.

Use the domain vocabulary from `CONTEXT.md` and `project-overview`. Use `docs/adr/` for past architectural decisions before suggesting something that's already been considered and rejected.

### 2. Present candidates

Show a numbered list of deepening opportunities. For each:

```
[N]. [Module name]
   Problem: [what makes it shallow or painful]
   Opportunity: [what a deeper version would look like]
   Test impact: [how this makes it easier to test]
   Effort: [small / medium / large]
```

### 3. Grill on the chosen candidate

Once the developer picks one, drop into a grilling conversation (load `grill-me`). Walk the design tree:
- What sits behind the seam?
- What tests survive the refactor?
- What tests need to change?
- What callers are affected?
- Can this be done in atomic PRs?

### 4. Update docs as decisions crystallise

- New domain term introduced? Add it to `CONTEXT.md`.
- Developer rejects a candidate with a load-bearing reason? Offer an ADR:
  > "Want me to record this as an ADR so future architecture reviews don't re-suggest it?"
  Only offer when the reason would genuinely help a future reviewer — skip ephemeral reasons ("not now") or self-evident ones.

### 5. Execute atomically

Each refactor is a separate PR with no feature work bundled in. Load `atomic-changes` before starting implementation. Load `tdd` — refactors need a green test suite before and after every step.

## When NOT to refactor

- When the codebase is in the middle of a feature sprint — finish the feature first
- When tests don't exist yet — add tests first, then refactor
- When the "shallow module" is a thin adapter over an external library — that's intentional
- When a seemingly redundant module carries important naming that aids navigation

## Output after the session

Update `docs/refactoring-plan.md` with any candidates that were identified but not immediately actioned, so they're not lost.