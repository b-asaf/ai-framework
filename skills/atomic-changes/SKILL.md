---
name: atomic-changes
description: Rules for breaking implementation into small, independently reviewable PRs. Applied by orchestrator, architect, and all implementation agents.
---

## Quick reference

- **One PR = one concern.** Reviewable in < 15 minutes, independently revertable.
- **Mandatory PR breakdown table** in every HLD before implementation starts.
- **Never mix:** refactor + feature, bug fix + new functionality, dep update + feature code, FE + BE.
- **Dep update always = separate PR 1**, feature using it = PR 2.
- **Micro-slice:** one behaviour, independently verifiable, never layer-based.
- **Deterministic backstop:** `pre-push` measures **meaningful changed lines** against the configured/default limit. It uses only deterministic Git/configuration evidence for the diff base and does not attempt semantic judgment. Everything above this line is agentic enforcement (architect/orchestrator/code-reviewer/gatekeeper); the hook is the deterministic structural backstop.

# Atomic Changes

## Ownership — who is responsible for what

| Agent | Responsibility |
|---|---|
| `@architect` | **Defines** the atomic breakdown as a mandatory PR table before any code is written. No HLD is complete without it. |
| `@orchestrator` | **Enforces** it during execution — tracks the current PR, prevents scope creep, advances one PR at a time |
| `@code-reviewer` | **Flags** violations — mixed scope is an immediate blocker, review stops until the PR is split |
| `@gatekeeper` | **Gates** it — atomicity is the first check in the final validation |
| `pre-push` hook | **Backstops** it — deterministically measures meaningful changed lines on every push. It does not decide semantic atomicity. |

---

## The rule

One PR = one concern. Every change must be small enough for a human to review in a single sitting without losing context.

**Atomicity is a semantic property; diff size is only a deterministic risk/backstop signal.**

## What "atomic" means

A PR is atomic when:
- It does exactly one thing
- It can be reverted without affecting unrelated functionality
- A reviewer can understand the full scope in under 15 minutes
- It passes all tests and lint independently

The first three properties require human/agent judgment. The final property is verified by tooling.

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

If a task cannot be broken into independently reviewable PRs, flag it to the developer and ask for scope reduction or phasing before starting implementation.

The ~400-line value is a **deterministic backstop threshold**, not a definition of atomicity. A change above it is not automatically non-atomic; it is a deterministic signal that requires splitting or an explicit reviewed exception.

---

## Deterministic backstop

Everything above this section is primarily agentic/engineering-process enforcement — the architect proposes the breakdown, the orchestrator tracks it, and code-reviewer/gatekeeper check semantic scope.

`pre-push` is the deterministic structural backstop.

### Protected branches

`protectedBranches` answers only:

> **"Where is direct push prohibited?"**

The hook builds the protected set deterministically from:

1. `main`, `master`, and `develop` as a compatibility fallback baseline
2. Git's `origin/HEAD` pointer, when available, as the repository's actual default branch
3. `.ai-framework.json` → `protectedBranches`, as additive project configuration

Configured entries may be exact branch names or simple trailing patterns such as `release/*`.

`origin/HEAD` identifies the default branch; it does **not** identify the target branch of every feature PR/MR.

### Diff base

The diff base answers a different question:

> **"What branch is this feature being compared against?"**

The preferred authoritative source when a PR/MR exists is its target branch. However, a plain local `pre-push` hook cannot know an external PR/MR target unless a provider integration supplies it. Therefore the hook itself uses only deterministic local evidence:

1. `.ai-framework.json` → `diffBaseBranch`, if configured
2. Git reflog evidence identifying an unambiguous protected branch as the feature branch's creation/checkout source
3. Otherwise **skip the diff-size check rather than guess**

A provider/CI integration may populate `diffBaseBranch` from the PR/MR target before running the gate.

The hook must never select the "first" protected branch or use an LLM to guess the base.

### Meaningful changed lines

The hook does not use raw `git diff --shortstat` as the atomicity measurement.

It deterministically excludes:
- blank-line changes
- whitespace-only changes
- import-only changes (including import reordering/path changes)
- pure file renames

All other added/deleted source lines count.

This is intentionally conservative. The hook does **not** attempt to determine whether two code changes are semantically related. That remains the responsibility of the architect, orchestrator, code-reviewer, and gatekeeper.

### Threshold and configuration

`.ai-framework.json` may configure:

```json
{
  "protectedBranches": ["main", "dev", "release/*"],
  "diffBaseBranch": "dev",
  "maxDiffLines": 400
}
```

- `protectedBranches`: direct-push protection only
- `diffBaseBranch`: deterministic diff comparison base
- `maxDiffLines`: meaningful changed-line backstop threshold

If `maxDiffLines` is absent, the default is `400`.

If no deterministic diff base can be identified, the hook skips the diff-size backstop with an explicit message; it does not silently compare against an arbitrary branch.

### Override

For a deliberate, reviewed exception:

```bash
SKIP_DIFF_SIZE_CHECK=1 git push
```

The override affects only the diff-size backstop. It does not bypass protected-branch enforcement.

This does not replace the agentic breakdown — a good PR breakdown table produced by `@architect` should mean this hook rarely triggers. The hook exists specifically as an independent deterministic safety net.

---

## Micro-slice rules

A slice is the unit of work delivered, reviewed, and verified independently. These rules define what makes a slice valid:

- **One behaviour per slice.** Each slice represents exactly one meaningful behaviour change. If it takes more than one implementation agent session to build, it is too large — split it.
- **Independent verifiability.** A slice must be reviewable and QA-verifiable without waiting for any other slice to be complete. If it cannot be verified independently, split it further.
- **Never layer-based.** Slices are never defined around technical layers (controllers, services, repositories) or internal refactors — those are engineering concerns, not delivery units. A slice is defined by a user-visible or externally-observable behaviour change.

Smaller is always better. Fewer, smaller slices complete the review cycle faster and keep implementation unblocked.