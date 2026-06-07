# CLAUDE.md
> Claude Code-specific instructions.
> SHARED.md is symlinked as `~/.claude/CLAUDE.md` — all shared rules apply.
> This file adds Claude Code-specific behaviour only.

---

## Tool permissions

Claude Code must respect these git permission boundaries at the tool level
(mirroring the `_opencode.json` permission block for OpenCode users):

| Command pattern        | Permission |
| ---------------------- | ---------- |
| `git status`           | allow      |
| `git log *`            | allow      |
| `git diff *`           | allow      |
| `git branch`           | allow      |
| `git branch *`         | allow      |
| `git checkout -b *`    | deny       |
| `git commit *`         | deny       |
| `git push *`           | deny       |
| `git merge *`          | deny       |
| `git rebase *`         | deny       |
| `git reset *`          | deny       |
| `git push --force *`   | deny       |
| everything else        | ask        |

## Skills location

Skills are in `~/.claude/skills/` (symlinked from this repo's `skills/` folder).
Load them by reading the relevant `skill.md` file before starting a task.

## Agents location

Sub-agent definitions are in `~/.claude/agents/`.

## Hooks

Event hooks are in `~/.claude/hooks/`. These fire automatically on Claude Code
lifecycle events — do not call them manually.
