# AGENTS.md

This file is loaded into every agent's context automatically via `_opencode.json`.
Every rule below applies to every agent, every session, without exception.

> 📖 Day-to-day guide: [workflow-guide.md](./workflow-guide.md)

---

## ⚡ DO THIS FIRST — before anything else

When a developer sends any message, the agent must do the following before responding to the request:

### Check 1 — First-run
Read `.opencode/skills/project-overview/SKILL.md`.
If it is empty, missing, or contains `[XXX]` placeholders:

**Stop. Say this:**
> "I need to run first-run analysis before I can help. This will scan the codebase and set up the framework. Shall I proceed?"

Then load the `first-run-analysis` skill and execute all steps before accepting any task.

### Check 2 — Branch guard
If the developer's message describes a task that requires writing or editing files:

**Stop. Say this before writing a single file:**
> "Before I make any changes, please confirm a feature branch is open.
> Please run: `git checkout -b <prefix>/<task-name>`
> Reply with 'done' when the branch is open."

Do not call `write` or `edit` until the developer confirms the branch is open.

Branch prefixes: `feat/` `fix/` `chore/` `refactor/` `docs/` `hotfix/` `release/`

---

## Non-negotiable rules

### 1. Git is the developer's responsibility
Agents may run: `git status`, `git log`, `git diff`, `git branch`
Agents must NEVER run: `git checkout -b`, `git commit`, `git push`, `git merge`, `git rebase`, `git reset`

### 2. Branch before any write
No `write` or `edit` tool call until the developer confirms a branch is open. See Check 2 above.

### 3. No 3rd party changes without approval
Any dependency add/remove/update requires explicit developer approval. Propose and wait.

### 4. First-run analysis
If `project-overview` contains `[XXX]` or is empty → run first-run analysis before any task. See Check 1 above.

### 5. Show before writing
Always show a plan and get confirmation before writing files.

### 6. Code principles
Apply Clean Code, SOLID, KISS, YAGNI to every file. Conflict resolution order: correctness → KISS → YAGNI → SOLID.

### 7. Atomic changes
One PR = one concern. See `atomic-changes` skill.

### 8. Git hooks
Check during first-run whether git hooks are installed. Warn on every handoff if not. See `git-hooks` skill.

### 9. Pre-implementation classification
Before writing, classify the task and load matching skills:

| Task type | Skills to load |
|---|---|
| Bug fix | `diagnose`, `tdd`, `zoom-out` (if unfamiliar), `pattern-enforcement` |
| New feature | `tdd`, `pattern-enforcement`, `code-standards`, `zoom-out` (if unfamiliar) |
| Refactor | `improve-codebase-architecture`, `code-standards`, `pattern-enforcement` |
| Chore / deps | `third-party-policy` |
| Docs change | `documentation` |

Tell the developer which skills were loaded before starting.

### 10. Mandatory post-implementation pipeline
After the last file write, before saying "done", run in order:

```
linter       → fix all violations
code-reviewer → review diff, no mercy
qa           → write missing tests, run full suite
gatekeeper   → validate every acceptance criterion
```

If any step fails → rework and re-run from linter.

### 11. Surgical changes
Touch only what the task requires. Every changed line must trace directly to the user's request.

- Do not improve, reformat, or refactor adjacent code
- Do not add docstrings, type hints, or logging that wasn't asked for
- Do not change style — match existing code even if you'd do it differently
- If you notice unrelated issues → mention them, never fix them silently
- Clean up only what **your changes** made unused (imports, variables, functions)

See the `surgical-changes` skill for the full rules.

---

## Agent roles

| Agent | Mode | Purpose |
|---|---|---|
| `orchestrator` | Primary | Routes tasks, coordinates agents, gates approval |
| `product-manager` | Primary | Clarifies requirements, writes specs |
| `architect` | Primary | Proposes HLD solutions |
| `backend` | Subagent | BE logic, services, repositories |
| `frontend` | Subagent | FE pages, state, data fetching |
| `ui` | Subagent | Components, styling, design system |
| `db` | Subagent | Persistence layer |
| `api` | Subagent | API contracts, 3rd party integrations |
| `linter` | Subagent | Linting tools, reports violations |
| `code-reviewer` | Subagent | Reviews diffs, no mercy |
| `qa` | Subagent | Writes and runs tests |
| `gatekeeper` | Subagent | Final validation before handoff |

---

## Task flow

```
Developer: "do X"
    ↓
CHECK 1: Is first-run done? → if not, run first-run-analysis
CHECK 2: Is branch open? → if not, ask developer to create one
    ↓
product-manager → requirements grill → confirmed spec
architect       → solution grill → confirmed HLD + PR breakdown
    ↓ developer confirms
implementation agents → implement (one PR at a time)
    ↓
linter → code-reviewer → qa → gatekeeper
    ↓ all PASS
"Ready. Please commit and push your branch."
```