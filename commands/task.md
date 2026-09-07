---
description: Start a new task — routes to the orchestrator, which runs the first-run gate, then the full clarify → design → plan-review → branch → implementation flow (see agents/orchestrator.md for the authoritative step sequence).
agent: orchestrator
---

Start a new development task.

Before Step 1, the orchestrator always checks `project-overview` for a
first-run state (unpopulated or containing `[XXX]`). If triggered, first-run
analysis runs to completion, with developer confirmation at each checkpoint,
before any task is accepted.

The task flow itself follows `agents/orchestrator.md`'s "On every task"
section exactly, step by step:

1. Clarify — route to `@product-manager`.
2. Design — route to `@architect`.
2b. Plan review (mandatory) — route to `@plan-reviewer`.
3. Confirm atomic PR breakdown.
4. Branch — propose the branch command for the current PR, wait for developer
   confirmation, before any file is written.
5. Implement (current PR only).
6. Lint & Review — `@code-reviewer`.
7. Test — `@qa`.
8. Final task summary.
9. Gate — `@gatekeeper`.
10. Handoff.

Do not skip, reorder, or renumber these steps here — `agents/orchestrator.md`
is the source of truth for step definitions and gating logic. This file is a
pointer only; if the two ever disagree, orchestrator.md wins and this file
should be corrected to match.