---
name: first-run-analysis
description: Full first-run analysis flow. Runs when project-overview is empty or contains [XXX]. Detects topology, repo state, languages, tools, conventions, and violations. Updates _opencode.json, project-overview, workflow-guide.md, Manual.md, and CONTEXT.md. Generates refactoring-plan.md if issues found.
---

# First-Run Analysis

Run all 7 steps in order. Do not skip or abbreviate. Confirm with the developer at each decision point before proceeding.

## Step 1 — Topology detection
Load the `repo-topology` skill and execute its Steps 1 and 2 (detect + confirm with developer).
Record the result in `project-overview` under `## Architecture topology` and update `_opencode.json` accordingly.

## Step 2 — Repo state detection
Classify each repo as new / partial / mature. For signals: read `references/detection-tables.md` (Repo state section).
Record in `project-overview` under `## Repo state`.

## Step 3 — Language and tool detection
Scan each repo. For detection signals: read `references/detection-tables.md` (Backend / Frontend sections).
Record all findings in `project-overview`.

## Step 3b — Run zoom-out per repo
Run `zoom-out` on each repo. Output feeds into Step 4 (knowing where to look) and Step 7 (CONTEXT.md vocabulary).

## Step 4 — Convention detection
Scan 10-20 representative files per repo. Detect:
- Test file placement (co-located / `__tests__/` / mirror package / mixed)
- Component structure, import style, naming conventions
- Error handling pattern, DTO usage, dependency injection style

## Step 5 — Convention evaluation
Evaluate each convention against Clean Code, SOLID, KISS, YAGNI, and internal consistency.
For severity classification: read `references/detection-tables.md` (Convention evaluation section).

## Step 6 — Generate refactoring-plan.md (if needed)
If any High or Medium issues found, generate `docs/refactoring-plan.md`.
For the template: read `references/refactoring-plan-template.md`.

Present summary:
```
📋 Refactoring plan generated: docs/refactoring-plan.md
🔴 [X] high  🟡 [Y] medium  🔵 [Z] low
Review before starting feature work. No changes made automatically.
```

> Architecture review is recurring — run `improve-codebase-architecture` every few days, not just at setup.

## Step 7 — Update all files
- **`project-overview`** — populate all sections, replace all `[XXX]`
- **`CONTEXT.md`** — load `domain-model` skill, create with top 5-10 domain terms discovered
- **`_opencode.json`** — replace `[XXX]`, apply topology changes (confirm with developer first)
- **`workflow-guide.md`** — append `## Project-specific notes` only if genuinely needed
- **`Manual.md`** — replace `[XXX]`, update workspace layout if microservices detected

## Completion message
```
✅ First-run analysis complete

Project: [name]  |  Architecture: [type]  |  Repos: [list with state]
Stack: BE [lang/framework]  |  FE [framework]

Files updated: project-overview ✅  _opencode.json ✅  CONTEXT.md ✅
[📋 refactoring-plan.md generated] ← only if applicable

Ready. What would you like to do first?
```