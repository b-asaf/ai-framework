# VSCODE.md
> VS Code GitHub Copilot specific instructions.
> Wired to `.github/copilot-instructions.md` at the project root by `setup.py`.
> This is a PROJECT-LEVEL file — run `python setup.py` from inside each project repo.
> All rules from SHARED.md apply. This file adds VS Code Copilot-specific behaviour only.

---

## Context loading

VS Code Copilot reads `.github/copilot-instructions.md` at the project root.
Unlike other tools, this wiring is per-project, not global.

To apply this framework to a new project:
```bash
cd /path/to/your-project
python /path/to/ai-framework/setup.py
```

This creates `.github/copilot-instructions.md` in your project pointing to this file.

## Tool permissions

VS Code Copilot does not have a declarative permission config.
Enforce git boundaries through instruction compliance:

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

## Path-scoped instructions (VS Code feature)

VS Code Copilot supports path-scoped instruction files under `.github/instructions/`.
Use these to override or extend the global rules for specific areas of the project:

```
.github/instructions/
  backend.instructions.md    # applyTo: "src/main/**"
  frontend.instructions.md   # applyTo: "src/client/**"
  tests.instructions.md      # applyTo: "**/*.test.*"
```

Each file uses a front-matter `applyTo` glob. Example:
```markdown
---
applyTo: "src/main/**"
---
Load the backend-dev-guidelines skill for all files in this path.
```

## Chat and inline completion behaviour

- Match existing code style exactly.
- Suggest only what the current context requires (surgical changes rule).
- If a suggestion would touch more than the current function or file, surface it
  as a chat suggestion for the developer to review scope.
- After generating, summarise what changed and flag anything needing review.
- One concern per conversation.
