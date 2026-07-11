# CLAUDE.md
> Claude Code-specific instructions.
> AGENTS.md is symlinked as `~/.claude/CLAUDE.md` — all shared rules apply.
> This file adds Claude Code-specific behaviour only.

---

## Tool permissions

Git permissions are defined in AGENTS.md Rule 1 — applies here without duplication.


## Skills location

Skills are in `~/.claude/skills/` (symlinked from this repo's `skills/` folder).
Load them by reading the relevant `skill.md` file before starting a task.

## Agents location

Sub-agent definitions are in `~/.claude/agents/`.

## Hooks

Event hooks are in `~/.claude/hooks/`. These fire automatically on Claude Code
lifecycle events — do not call them manually.
