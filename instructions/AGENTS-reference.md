# AGENTS-reference.md
> Reference material loaded on-demand by the orchestrator when making routing decisions.
> NOT loaded globally — loaded once at task start by the orchestrator.

---

## Agent roles

| Agent                    | Mode     | Purpose                                          |
| ------------------------ | -------- | ------------------------------------------------ |
| `orchestrator`           | Primary  | Routes tasks, coordinates agents, gates approval |
| `product-manager`        | Primary  | Clarifies requirements, writes specs             |
| `architect`              | Primary  | Proposes HLD solutions                           |
| `plan-reviewer`          | Primary  | Validates HLD before implementation begins       |
| `refactor-planner`       | Primary  | Plans safe incremental refactors                 |
| `backend`                | Subagent | BE logic, services, repositories                 |
| `frontend`               | Subagent | FE pages, state, data fetching                   |
| `ui`                     | Subagent | Components, styling, design system               |
| `db`                     | Subagent | Persistence layer                                |
| `api`                    | Subagent | API contracts, 3rd-party integrations            |
| `code-reviewer`          | Subagent | Lints, scans, reviews diffs — no mercy           |
| `qa`                     | Subagent | Writes and runs tests                            |
| `gatekeeper`             | Subagent | Final validation before handoff                  |
| `frontend-error-fixer`   | Subagent | JS/TS build and runtime error diagnosis          |
| `web-research-specialist`| Subagent | Searches web for 3rd-party solutions             |

---

## Skill routing

Handled by `skill-rules.json` (ad-hoc/off-flow requests, keyword+intent matched,
priority-ordered, capped) and by each agent's own "Always load"/"Load when
relevant" list (inside the structured task flow — see Rule 8 in `AGENTS.md`).
This file intentionally does not duplicate that table anymore — keeping the
routing logic in one place per scope avoids the two mechanisms drifting apart
and double-loading skills.

---

## Task flow

```
Developer: "do X"
    ↓
CHECK 1: project-overview unpopulated?  → run first-run-analysis
CHECK 2: working branch mismatch?           → propose → confirm → git checkout -b
    ↓
@product-manager  → requirements grill → confirmed spec
@architect        → solution grill     → confirmed HLD + PR breakdown
@plan-reviewer    → validate HLD       → APPROVED / CHANGES / BLOCKED
    ↓ approved
implementation agents → one PR at a time
    ↓
@code-reviewer (lint + scan + review) → @qa → @gatekeeper
    ↓ all PASS (gatekeeper also persists any newly discovered facts to project-overview)
"Ready. Please commit and push your branch."
```

---

## Context budget rule

If the orchestrator has produced more than **8 agent responses** in a session,
or any single response exceeds **~3,000 tokens**, load the `handoff` skill
before the next step and propose compacting the session.
