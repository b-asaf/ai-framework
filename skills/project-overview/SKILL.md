---
name: project-overview
description: Project-specific context. Populated automatically on first run. Every agent loads stack.md first. If it contains [XXX] or is empty, trigger first-run analysis before proceeding. Load sub-files selectively based on task type.
---

# Project Overview

> **Status:** [UNPOPULATED — first-run analysis required]
> When an agent detects this status, perform a full codebase scan and populate
> all sub-files before doing anything else. Confirm findings with the developer.

## Sub-files — load selectively

| File | Load when |
|---|---|
| `sub/stack.md` | **Every agent, every task** — languages, frameworks, commands |
| `sub/patterns.md` | Implementation agents, code-reviewer, plan-reviewer |
| `sub/topology.md` | Orchestrator, architect, tasks spanning multiple services |
| `sub/tooling.md` | Linter, first-run analysis |
| `sub/localization.md` | Any task touching UI text, strings, or directional layout |

Always load `sub/stack.md` first. Load other sub-files only when the task requires them.
