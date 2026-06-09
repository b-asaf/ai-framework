# SHARED.md
> Single source of truth for AI behavior rules.
> Symlinked / copied into every tool's config location by `setup.py`.
> Every rule below applies to every agent, every session, without exception.
>
> Agent roles, task flow diagram, and skill routing table are in `SHARED-reference.md`.
> The orchestrator loads that file when making routing decisions.

---

## ⚡ DO THIS FIRST — before anything else

When a developer sends any message, do the following before responding:

### Check 1 — First-run

Read the project's `project-overview` skill file.

If it is empty, missing, or contains `[XXX]` placeholders — **stop. Say this:**

> "I need to run first-run analysis before I can help. This will scan the
> codebase and set up the framework. Shall I proceed?"

Then execute all first-run steps before accepting any task.

### Check 2 — Branch guard

If the developer's message requires writing or editing files — **stop first:**

> "Before I make any changes I'll create a branch. I propose:
> `<prefix>/<task-name>`
> Reply 'yes' to confirm and I'll create it, or tell me a different name."

Wait for confirmation. Once confirmed, run `git checkout -b <name>`.
Only after the branch exists may any file be written or edited.

Branch prefixes: `feat/` `fix/` `chore/` `refactor/` `docs/` `hotfix/` `release/`
Name rules: lowercase, hyphens only, ≤ 50 chars, derived from the task.

---

## Non-negotiable rules

### 1. Git — allowed and forbidden commands

**Allowed:** `git status`, `git log`, `git diff`, `git branch`,
`git checkout -b` (only after developer confirms — see Check 2)

**Never run:** `git commit`, `git push`, `git merge`,
`git rebase`, `git reset`, `git push --force`

### 2. Branch before any write

No file write or edit until the branch is created. See Check 2.

### 3. No 3rd-party changes without approval

Any dependency add / remove / update — propose and wait for explicit approval.

### 4. First-run is mandatory

`project-overview` contains `[XXX]` or is empty → run first-run analysis first.

### 5. Show before writing

Always show a plan and get confirmation before writing files.

### 6. Code principles

Apply Clean Code, SOLID, KISS, YAGNI to every file.
Conflict resolution: correctness → KISS → YAGNI → SOLID.

### 7. Atomic changes

One PR = one concern.

### 8. Pre-implementation skill loading

Classify the task, then load matching skills. Routing table is in `SHARED-reference.md`.
Tell the developer which skills were loaded before starting.

### 9. Post-implementation pipeline

After the last file write, before saying "done", run in order:
```
linter → code-reviewer → qa → gatekeeper
```
If any step fails → rework and re-run from linter.

### 10. Surgical changes

Touch only what the task requires. Every changed line traces to the request.
- Do not improve, reformat, or refactor adjacent code
- Do not add docstrings, logging, or annotations not asked for
- Match existing style — do not impose preferences
- Mention unrelated issues; never fix them silently
- Clean up only what your changes made unused
