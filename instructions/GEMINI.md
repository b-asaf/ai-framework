# GEMINI.md
> Gemini CLI global instructions file (`~/.gemini/GEMINI.md`).
> Imports shared rules, then adds Gemini-specific behaviour.
> RTK appends its block below — the @import preserves SHARED.md as the source of truth.

@./SHARED.md

---

## Gemini CLI — additional rules

### Tool permissions

Gemini CLI has no declarative permission config. Enforce these boundaries
through instruction compliance in addition to the rules in SHARED.md:

| Command pattern     | Behaviour                                                                  |
| ------------------- | -------------------------------------------------------------------------- |
| `git status`        | allowed                                                                    |
| `git log`           | allowed                                                                    |
| `git diff`          | allowed                                                                    |
| `git branch`        | allowed                                                                    |
| `git checkout -b *` | only after developer confirms proposed branch name — see Check 2           |
| `git commit *`      | never                                                                      |
| `git push *`        | never                                                                      |
| `git merge *`       | never                                                                      |
| `git rebase *`      | never                                                                      |
| `git reset *`       | never                                                                      |

### Skills

Gemini CLI has native skill discovery under `~/.gemini/skills/`.
Skills are symlinked there by `setup.py`. At task start, read
`skill-rules.json` and load matching skills by reading their SKILL.md file.

### Completion behaviour

- Match existing code style exactly — no auto-formatting
- Surgical changes only — touch nothing outside the task scope
- After generating code, summarise what changed and flag anything needing review
