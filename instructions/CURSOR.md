# CURSOR.md
> Cursor (Composer / Chat) specific instructions.
> Symlinked to `~/.cursor/rules/shared.mdc` by `setup.py`.
> All rules from SHARED.md apply. This file adds Cursor-specific behaviour only.

---

## Context loading

Cursor reads `.cursor/rules/` at the project level and `~/.cursor/rules/` globally.
This file is wired globally. All shared rules (branch guard, first-run, git restrictions,
post-implementation pipeline) are in `SHARED.md` and apply here without repetition.

## Tool permissions

Cursor does not have a declarative permission config. Enforce these git boundaries
through instruction compliance:

| Command pattern     | Behaviour                                                          |
| ------------------- | ------------------------------------------------------------------ |
| `git status`        | allowed                                                            |
| `git log`           | allowed                                                            |
| `git diff`          | allowed                                                            |
| `git branch`        | allowed                                                            |
| `git checkout -b *` | only after developer confirms proposed branch name — see SHARED.md Check 2 |
| `git commit *`      | never                                                              |
| `git push *`        | never                                                              |
| `git merge *`       | never                                                              |
| `git rebase *`      | never                                                              |
| `git reset *`       | never                                                              |

## Composer behaviour (multi-file edits)

- Always propose a plan in Composer before generating any multi-file edit.
- Apply the branch guard (SHARED.md Check 2) before accepting a Composer run that writes files.
- Each Composer run must address exactly one concern (atomic changes rule).
- After Composer completes, load and run the post-implementation pipeline:
  linter → code-reviewer → qa → gatekeeper.

## Chat behaviour

- If the request is ambiguous, ask one clarifying question before generating any code.
- After generating code, summarise what changed and flag anything that needs review or testing.
- Match existing code style exactly — do not auto-apply formatting changes.

## Skills and agents

Skills live in `~/.cursor/rules/` if you want to reference them directly, or in the
symlinked `.opencode/skills/` folder at the repo root. Load the relevant skill file
by reading it before starting a task.
