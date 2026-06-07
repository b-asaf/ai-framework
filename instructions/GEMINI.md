# GEMINI.md
> Gemini CLI-specific instructions.
> All rules from SHARED.md apply. This file adds Gemini CLI-specific behaviour only.

---

## Context loading

Gemini CLI reads `GEMINI.md` from the project root or `~/.gemini/GEMINI.md` globally.
All shared rules (branch guard, first-run, git restrictions, post-implementation
pipeline) are inherited from `instructions/SHARED.md`, which is symlinked to
`~/.gemini/GEMINI.md` by `setup.py`.

## Tool permissions

Gemini CLI does not have a declarative permission config like `_opencode.json`.
Enforce these git boundaries through instruction compliance:

| Command pattern      | Behaviour    |
| -------------------- | ------------ |
| `git status`         | allowed      |
| `git log`            | allowed      |
| `git diff`           | allowed      |
| `git branch`         | allowed      |
| `git checkout -b *`  | only after developer confirms proposed branch name — see SHARED.md Check 2 |
| `git commit *`       | never        |
| `git push *`         | never        |
| `git merge *`        | never        |
| `git rebase *`       | never        |
| `git reset *`        | never        |

## Skills and agents

Gemini CLI does not have a native skill/agent loading system.
Load skills by reading the relevant markdown file at the start of a task and
summarising its rules before proceeding. Skills live in `skills/` in this repo.

## Completion behaviour

- Match the existing code style exactly
- Surgical changes only — touch nothing outside the task scope
- After generating code, summarise what changed and flag anything that needs
  testing or review
