# GEMINI.md
> Gemini CLI global instructions file (`~/.gemini/GEMINI.md`).
> Imports shared rules, then adds Gemini-specific behaviour.
> RTK appends its block below — the @import preserves AGENTS.md as the source of truth.

@../AGENTS.md

---

## Gemini CLI — additional rules

### Tool permissions

Gemini CLI has no declarative permission config. The git permissions defined
in AGENTS.md Rule 1 apply — enforce through instruction compliance.

### Skills

Gemini CLI has native skill discovery under `~/.gemini/skills/`.
Skills are symlinked there by `setup.py`. At task start, read
`skill-rules.json` and load matching skills by reading their SKILL.md file.

### Completion behaviour

- Match existing code style exactly — no auto-formatting
- Surgical changes only — touch nothing outside the task scope
- After generating code, summarise what changed and flag anything needing review
