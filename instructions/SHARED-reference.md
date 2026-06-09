# SHARED-reference.md
> Reference material loaded on-demand by the orchestrator when making routing decisions.
> NOT loaded globally on every session — loaded once at task start by the orchestrator.
> Keep this file in sync with SHARED.md if rules change.

---

## Agent roles

| Agent             | Mode     | Purpose                                          |
| ----------------- | -------- | ------------------------------------------------ |
| `orchestrator`    | Primary  | Routes tasks, coordinates agents, gates approval |
| `product-manager` | Primary  | Clarifies requirements, writes specs             |
| `architect`       | Primary  | Proposes HLD solutions                           |
| `plan-reviewer`   | Primary  | Validates HLD before implementation begins       |
| `refactor-planner`| Primary  | Plans safe incremental refactors                 |
| `backend`         | Subagent | BE logic, services, repositories                 |
| `frontend`        | Subagent | FE pages, state, data fetching                   |
| `ui`              | Subagent | Components, styling, design system               |
| `db`              | Subagent | Persistence layer                                |
| `api`             | Subagent | API contracts, 3rd-party integrations            |
| `linter`          | Subagent | Linting tools, reports violations                |
| `code-reviewer`   | Subagent | Reviews diffs, no mercy                          |
| `qa`              | Subagent | Writes and runs tests                            |
| `gatekeeper`      | Subagent | Final validation before handoff                  |
| `frontend-error-fixer` | Subagent | JS/TS build and runtime error diagnosis   |
| `web-research-specialist` | Subagent | Searches web for 3rd-party solutions   |

---

## Skill routing table

Load these skills before starting implementation. Tell the developer which were loaded.

| Task type    | Skills to load                                                                      |
| ------------ | ----------------------------------------------------------------------------------- |
| Bug fix      | `diagnose`, `tdd`, `zoom-out` (if unfamiliar), `pattern-enforcement`                |
| New feature  | `tdd`, `pattern-enforcement`, `code-standards`, `zoom-out` (if unfamiliar)          |
| Refactor     | `refactor-planner` (agent), `improve-codebase-architecture`, `code-standards`, `pattern-enforcement` |
| Chore / deps | `third-party-policy`                                                                |
| Docs change  | `documentation`                                                                     |
| Architecture review | `improve-codebase-architecture`, `zoom-out`, `pattern-enforcement`         |
| Frontend error | `diagnose`, `frontend-error-fixer` (agent), `clean-code-error-handling`           |
| Unknown 3rd-party issue | `web-research-specialist` (agent) before any implementation            |

---

## Task flow

```
Developer: "do X"
    ↓
CHECK 1: project-overview unpopulated?  → run first-run-analysis
CHECK 2: no branch open?                → propose name → confirm → git checkout -b
    ↓
@product-manager  → requirements grill → confirmed spec
@architect        → solution grill     → confirmed HLD + PR breakdown
@plan-reviewer    → validate HLD       → APPROVED / APPROVED WITH CHANGES / BLOCKED
    ↓ developer confirms
implementation agents → one PR at a time
    ↓
@linter → @code-reviewer → @qa → @gatekeeper
    ↓ all PASS
"Ready. Please commit and push your branch."
```

---

## Context budget rule

If the orchestrator has produced more than **8 agent responses** in a session,
or any single response exceeds **~3,000 tokens**, load the `handoff` skill
before the next step and propose compacting the session.
