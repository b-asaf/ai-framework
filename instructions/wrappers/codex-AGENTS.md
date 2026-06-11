# AGENTS.md — Codex CLI
# This file imports the shared rules then adds Codex-specific configuration.
# RTK appends its block here — the @import keeps SHARED.md as source of truth.

@../SHARED.md

---

## Codex CLI — additional configuration

### Skills

skills:
  path: ~/.codex/skills
  autoload: false

Load skills on-demand at task start by reading the relevant SKILL.md file.
Use skill-rules.json to determine which skills to load for each task type.

### Behaviour

- Default to implementing changes rather than only suggesting them
- Read relevant files before answering questions about the codebase
- Propose a plan and wait for confirmation before writing files
