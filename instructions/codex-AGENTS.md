# AGENTS.md — Codex CLI
# Imports shared rules. RTK can safely append its block here.

@../AGENTS.md

---

## Codex CLI — additional configuration

### Skills

skills:
  path: ~/.codex/skills
  autoload: false

Load skills on-demand at task start by reading the relevant SKILL.md.
Use skills/skill-routing/skill-rules.json to determine which skills to load.
