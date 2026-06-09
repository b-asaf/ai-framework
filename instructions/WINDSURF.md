# WINDSURF.md
> Windsurf (Codeium) specific instructions.
> Symlinked to `~/.codeium/windsurf/memories/global-rules.md` by `setup.py`.
> All rules from SHARED.md apply. This file adds Windsurf-specific behaviour only.

---

## Context loading

Windsurf reads `.windsurfrules` at the project level for project-specific rules.
This file is wired globally via the memories system. All shared rules apply.

## Tool permissions

Windsurf does not have a declarative permission config. Enforce git boundaries
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

## Cascade (agentic) behaviour

- Propose a plan before starting any multi-file Cascade run.
- Apply the branch guard (SHARED.md Check 2) before writing any file.
- Each Cascade run addresses exactly one concern.
- After Cascade completes, run: linter → code-reviewer → qa → gatekeeper.

## Inline completion behaviour

- Match the existing code style exactly — no auto-formatting.
- Suggest only what the current cursor context requires (surgical changes rule).
- If a completion would touch more than the immediate function, surface it as
  a chat suggestion so the developer can review scope first.

## Chat behaviour

- One concern per conversation.
- Ask one clarifying question if the request is ambiguous before generating code.
- After generating, summarise what changed and flag anything needing review.

## Skills

Skills live in `.opencode/skills/` at the repo root. Load the relevant skill
by reading the file before starting a task.
