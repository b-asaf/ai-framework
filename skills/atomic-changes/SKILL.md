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

Protecting a branch is the git host's job (DEC-029): set a branch policy on GitHub, GitLab or Azure DevOps. The pre-push gate does not block a push by branch name, and no key in `.ai-framework.json` configures protection.

### Diff base

The diff base answers a different question:

> **"What branch is this feature being compared against?"**

The preferred authoritative source when a PR/MR exists is its target branch. However, a plain local `pre-push` hook cannot know an external PR/MR target unless a provider integration supplies it. Therefore the push gate uses only deterministic local evidence:

1. `.ai-framework.json` → `diffBaseBranch`, if configured (it must resolve to a commit, otherwise the push is blocked)
2. Origin's default branch (`origin/HEAD`)
3. Otherwise the push is **blocked** with a message that names the fix (DEC-020); the check never skips

A provider/CI integration may populate `diffBaseBranch` from the PR/MR target before running the gate. First-run asks the developer for the PR target branch and writes `diffBaseBranch` when it is not the default branch.

The hook must never pick a branch by its name or use an LLM to guess the base.

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
  "diffBaseBranch": "dev",
  "maxDiffLines": 400
}
```

- `diffBaseBranch`: deterministic diff comparison base
- `maxDiffLines`: meaningful changed-line backstop threshold

If `maxDiffLines` is absent, the default is `400`.

If no diff base can be identified, the push is blocked with a message that names the fix (DEC-020); the check never skips and never compares against an arbitrary branch. It runs in the Python push gate (`execution/verification/checks/diff_size.py`).

### Override

For a deliberate, reviewed exception:

```bash
SKIP_DIFF_SIZE_CHECK=1 git push
```

The override affects only the diff-size backstop. It does not bypass protected-branch enforcement.

A reviewed exception can also be recorded in the branch itself (DEC-025). One line of a commit message of the branch reads:

```text
Diff-Size-Approved: <lines> <reason>
```

`<lines>` is a whole number of 1 or more (at most 9 digits) and `<reason>` is not empty. The limit for that branch is then the larger of `maxDiffLines` and the largest approved number: the push passes up to that number and is blocked again above it. The gate reads the commits from the merge-base to the pushed commit, the range it measures, so an approval made before an earlier push still counts. A line that starts with `Diff-Size-Approved:` in any other form blocks the push and names the commit, so no other message line may start with those words.

Only the developer decides such an exception. An agent never writes this line on its own and never suggests it as a way past a block: a push blocked for size goes back to the developer.

This does not replace the agentic breakdown — a good PR breakdown table produced by `@architect` should mean this hook rarely triggers. The hook exists specifically as an independent deterministic safety net.

---

## Micro-slice rules

A slice is the unit of work delivered, reviewed, and verified independently. These rules define what makes a slice valid:

- **One behaviour per slice.** Each slice represents exactly one meaningful behaviour change. If it takes more than one implementation agent session to build, it is too large — split it.
- **Independent verifiability.** A slice must be reviewable and QA-verifiable without waiting for any other slice to be complete. If it cannot be verified independently, split it further.
- **Never layer-based.** Slices are never defined around technical layers (controllers, services, repositories) or internal refactors — those are engineering concerns, not delivery units. A slice is defined by a user-visible or externally-observable behaviour change.

Smaller is always better. Fewer, smaller slices complete the review cycle faster and keep implementation unblocked.