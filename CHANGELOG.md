# Changelog

All notable changes to ai-framework are documented here.
Format: [version] — [date] — [summary]

Changes are made on `develop` branch and merged to `main` when stable.

---

## Unreleased (develop)

- Per-agent model tiers (Opus/Sonnet/Haiku based on task complexity)
- Token monitoring: opencode-tokenscope, opencode-usage wired via setup.py
- Guarded commit/push/PR flow (Check 4 in AGENTS.md)
- `gh` CLI auto-install in setup.py
- Rule 14: auto-trigger caveman + handoff at context budget threshold
- 8 skills set to disable-model-invocation: true
- Quick reference sections on all skills > 40 lines
- All agents load project-overview sub-files selectively
- Token reduction stack: RTK + Headroom + Token Optimizer

## v1.0.0 — initial stable baseline

- 16 agents, 39 skills, 4 slash commands
- OpenCode as primary tool, global wiring via setup.py
- AGENTS.md with 14 rules (XML-tagged)
- Per-agent model tiering
- Branching policy enforced via Check 2
- Post-implementation pipeline: linter → code-reviewer → qa → gatekeeper
- session-end.js hook for auto session summary
