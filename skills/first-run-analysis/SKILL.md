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

Everything this skill generates goes into the folder for generated files, except `.ai-framework.json`,
`CONTEXT.md` and `_opencode.json`, which stay where they are (DEC-026). That folder is `.ai-framework/` at
the repository root, or the path in `generatedDir` in `.ai-framework.json` (AGENTS.md Check 1 says how to
read it). `<generated folder>` below means that folder.

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

## Step 3c — Base branch (per repo)

Find the branch the developer's PRs target, for each repo. Run `python "$HOME/.config/opencode/scripts/git-context.py"` from that repo and read the `BASE:` line of the `--- ahead ---` section (the branch `origin/HEAD` points to; there is no such line when none was found). Ask once per repo: "Which branch do your PRs target? Default: `<BASE>`." (without the default when there is no `BASE:` line).

- If the answer is the default (ignore a leading `origin/` when comparing), write nothing.
- Otherwise, or when there was no `BASE:` line, Step 7 writes the answer as `diffBaseBranch`, as `origin/<branch>`. If that ref does not exist locally, tell the developer to run `git fetch`.

The size, dependency and quick-lane checks measure a new branch against this base. A repo whose `origin/HEAD` is not where its work starts would be measured against the wrong branch (DEC-029).

## Step 3d — Code graph (per repo)

Build the code graph of each repo: run `python "$HOME/.config/opencode/scripts/graph.py" build` from that repo (code only, no API key, no cost). The graph goes into `<generated folder>/graphify/`, which gets its own `.gitignore`, so nothing of it is committed. On `STATUS: ERROR` tell the developer the `REASON:` and go on: the graph is a help, not a gate. Never run `graphify install`, `graphify uninstall` or `graphify hook install` (DEC-030).

## Step 4 — Convention detection

Detect:

- Test file placement (co-located / `__tests__/` / mirror package / mixed)
- Component structure, import style, naming conventions
- Error handling pattern, DTO usage, dependency injection style

## Step 5 — Convention evaluation

Evaluate each convention against Clean Code, SOLID, KISS, YAGNI, and internal consistency.
For severity classification: read `references/detection-tables.md` (Convention evaluation section).

## Step 6 — Generate refactoring-plan.md (if needed)

If any High or Medium issues found, generate `<generated folder>/refactoring-plan.md`.
For the template: read `references/refactoring-plan-template.md`.

Present summary:

```
📋 Refactoring plan generated: <generated folder>/refactoring-plan.md
🔴 [X] high  🟡 [Y] medium  🔵 [Z] low
Review before starting feature work. No changes made automatically.
```

> Architecture review is recurring — run `improve-codebase-architecture` every few days, not just at setup.

## Step 7 — Update all files

- `project-overview` — populate all sections, replace all `[XXX]`. **Write the
  populated content to the project's own repo** (in `<generated folder>/project-overview/`,
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
- **`.ai-framework.json`** — write to the root of **each individual repo** (not the shared framework install): `{"lint": "<cmd or empty string>", "format": "<cmd or empty string>", "test": "<cmd or empty string>"}` (optional: `coverage.minChangedLines`, a whole number from 0 to 100, default 90, 0 means no minimum, is the changed-line coverage minimum; write it only if the developer names a number), mirroring the Lint/Format/Test command fields you just wrote into that repo's `stack.md` (a field recorded as "none configured" is written as an empty string, and that stage is skipped). At least one of the three must be non-empty, because the pre-push gate blocks a repo with no command at all. This is what the `pre-push` git hook reads to run `build-verify` structurally — it must live inside the project's own repo, not the shared skills location, since the hook has no other way to find it. Commit it. The optional key `generatedDir` (a relative path made of letters, digits, spaces and `. _ - /`, with no `..`) moves the folder for generated files; write it only if the developer names a folder. The optional key `diffBaseBranch` (`origin/<branch>`) is written only as Step 3c says.

## Completion message

```
✅ First-run analysis complete

Project: [name]  |  Architecture: [type]  |  Repos: [list with state]
Stack: BE [lang/framework]  |  FE [framework]

Files updated: project-overview ✅  _opencode.json ✅  CONTEXT.md ✅  .ai-framework.json ✅
[📋 refactoring-plan.md generated] ← only if applicable

Ready. What would you like to do first?
```