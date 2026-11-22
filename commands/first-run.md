---
description: Manually trigger first-run analysis for the current project. Use when project-overview is stale or [XXX] placeholders need refreshing.
---

Run a full first-run analysis on the current project:

1. Load `first-run-analysis` skill.
2. Scan the codebase — detect topology, stack, build tools, test frameworks, linters, patterns.
3. Populate all `project-overview/sub/*.md` files in the folder for generated files (`.ai-framework/`, or `generatedDir` in `.ai-framework.json`; see AGENTS.md Check 1) — replace every `[XXX]` with real values.
4. Confirm findings with the developer before writing.
5. Write `refactoring-plan.md` in that folder if issues are found.
