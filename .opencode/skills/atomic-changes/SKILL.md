---
name: atomic-changes
description: Rules for breaking implementation into small, independently reviewable PRs. Applied by orchestrator, architect, and all implementation agents.
---

# Atomic Changes

## Ownership — who is responsible for what

| Agent | Responsibility |
|---|---|
| `@architect` | **Defines** the atomic breakdown as a mandatory PR table before any code is written. No HLD is complete without it. |
| `@orchestrator` | **Enforces** it during execution — tracks the current PR, prevents scope creep, advances one PR at a time |
| `@code-reviewer` | **Flags** violations — mixed scope is an immediate blocker, review stops until the PR is split |
| `@gatekeeper` | **Gates** it — atomicity is the first check in the final validation |

---

## The rule
One PR = one concern. Every change must be small enough for a human to review in a single sitting without losing context.

## What "atomic" means
A PR is atomic when:
- It does exactly one thing
- It can be reverted without affecting unrelated functionality
- A reviewer can understand the full scope in under 15 minutes
- It passes all tests and lint independently

## The mandatory architect PR breakdown table

Every HLD must include this table before implementation begins. The developer approves it explicitly.

```
| PR | Branch             | Agent(s)  | What it contains              | Depends on |
|----|--------------------|-----------|-------------------------------|------------|
| 1  | feat/csv-utility   | @backend  | CSV export utility class only | —          |
| 2  | feat/csv-endpoint  | @backend  | Export controller + service   | PR 1       |
| 3  | feat/csv-client    | @frontend | Typed API client for export   | PR 2       |
| 4  | feat/csv-button    | @frontend | Export button UI wiring       | PR 3       |
```

Each row = one branch = one PR = one agent's session.

## How to break down a feature

When an architect proposes a solution, it must include an implementation order that breaks work into atomic steps. Example for "add user export to CSV":

```
PR 1 — feat: add CSV export utility (backend)
  → pure utility, no business logic, fully testable in isolation

PR 2 — feat: add export endpoint (backend)
  → controller + service method, depends on PR 1

PR 3 — feat: add export API client (frontend)
  → typed client for the new endpoint, no UI yet

PR 4 — feat: add export button to user list (frontend)
  → UI wiring, depends on PR 3
```

Each PR is mergeable and deployable independently.

## What must NOT be in the same PR
- A refactor AND a feature
- A bug fix AND new functionality
- Changes to two unrelated modules
- A dependency update AND feature code using that dependency

## Dependency updates
If a 3rd party dependency must be updated as part of a feature, it is always a separate PR:
```
PR 1 — chore: update [package] to [version]  ← developer approves this first
PR 2 — feat: use new [package] API in [feature]
```

## When a task is too large
If a task cannot be broken into PRs each under ~400 lines of meaningful change, flag it to the developer and ask for scope reduction or phasing before starting implementation.