---
name: first-run-analysis
description: Runs automatically when project-overview is empty or contains [XXX] (via AGENTS.md Check 1 and Rule 4). Also manually invokable when the developer wants to refresh the project scan.
---

## Quick reference

**7 steps in order:** topology detection → repo state → language/tool detection → zoom-out per repo → convention detection → refactoring-plan.md (if issues) → update all files (project-overview, CONTEXT.md, opencode.json, workflow-guide.md)

**Trigger:** `project-overview` contains `[XXX]` or is empty.

**Confirm with developer** at each decision point before proceeding.

**Completion message** includes: project name, architecture type, repos, stack, files updated.

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

If the `graphify` skill is available and `graphify-out/graph.json` exists (or can be built), verify that the graph is fresh before using it. When `graphify-out/graph.json` is missing or stale, run `graphify update .` first, then use `graphify query`/`graphify explain` against the real `calls`/`imports`/`inherits` edges to identify where patterns repeat across the whole repo, not just a sample — then confirm against the specific files found. If Graphify is unavailable or cannot refresh the artifact, scan 10-20 representative files per repo.

Detect:

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

- `project-overview` — populate all sections, replace all `[XXX]`. **Write the
  populated content to the project's own repo** (e.g. `docs/project-overview/`,
  mirroring the `sub/` folder structure), **never to the shared ai-framework skills
  location.** The shared `skills/project-overview/` stays a generic, unpopulated
  template for every project — see decisions/DEC-003 for why this matters.
  **Before writing:** confirm you are populating the copy inside the project's own repo,
  not the shared framework install. If `skills/project-overview/SKILL.md`'s Status line
  ever shows a specific project name (not `[UNPOPULATED]`), STOP — this means a previous
  run wrote project data into the shared repo by mistake, and every other project opened
  through this install is now seeing that data instead of triggering its own first-run
  analysis. Reset it to the template state and escalate before proceeding.
- **`CONTEXT.md`** — load `domain-model` skill, create with top 5-10 domain terms discovered
- **`_opencode.json`** — replace `[XXX]`, apply topology changes (confirm with developer first)
- **`workflow-guide.md`** — append `## Project-specific notes` only if genuinely needed
- **`Manual.md`** — replace `[XXX]`, update workspace layout if microservices detected
- **`.ai-framework.json`** — write to the root of **each individual repo** (not the shared framework install): `{"lint": "<cmd>", "format": "<cmd or empty string>", "test": "<cmd>"}`, mirroring the Lint/Format/Test command fields you just wrote into that repo's `stack.md`. This is what the `pre-push` git hook reads to run `build-verify` structurally — it must live inside the project's own repo, not the shared skills location, since the hook has no other way to find it. Commit it.
- **`graphify-out/`** — if the `graphify` skill is available and hasn't been run in this
  repo yet:
  1. Build the initial graph: run `graphify_smart_viz.py .` from the ai-framework repo
     (auto-detects LLM key availability, defaults to `--code-only` if none is set —
     see `skills/graphify/SKILL.md`).
  2. Wire the always-on nudge for the current platform: `graphify opencode install`
     (or `graphify claude install` / `graphify codex install` / `graphify gemini
     install` — match whichever tool this session is running in).
  3. Wire the rebuild hooks: `graphify hook install`.
  4. **Commit** `graphify-out/` (except `graphify-out/cost.json`, which stays local),
     plus whatever platform instruction file step 2 modified (e.g. the graphify
     section added to this project's own `AGENTS.md`).

  Without step 4, teammates pulling never get a current graph. Without steps 2–3, the
  graph gets built once but is never consulted automatically and never kept fresh —
  see `decisions/DEC-005` for why this was previously a separate manual step and isn't
  anymore.

## Completion message

```
✅ First-run analysis complete

Project: [name]  |  Architecture: [type]  |  Repos: [list with state]
Stack: BE [lang/framework]  |  FE [framework]

Files updated: project-overview ✅  _opencode.json ✅  CONTEXT.md ✅  .ai-framework.json ✅  graphify-out ✅  graphify wiring ✅
[📋 refactoring-plan.md generated] ← only if applicable

Ready. What would you like to do first?
```