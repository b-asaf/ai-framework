---
description: Manually trigger first-run analysis for the current project. Use when project-overview is stale or [XXX] placeholders need refreshing.
---

Run a full first-run analysis on the current project:

1. Load `first-run-analysis` skill.
2. Scan the codebase — detect topology, stack, build tools, test frameworks, linters, patterns.
3. Populate all `project-overview/sub/*.md` files — replace every `[XXX]` with real values.
4. Confirm findings with the developer before writing.
5. Write `docs/refactoring-plan.md` if issues are found.
