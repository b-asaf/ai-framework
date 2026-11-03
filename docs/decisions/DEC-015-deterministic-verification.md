# DEC-015 — Deterministic verification

**Status:** Accepted (the principle). Sections marked "to be completed" are filled in by steps 3A.1, 3C and 4.5 of `docs/transition-plan.md`.
**Date:** 2026-10-06

## Context

- DEC-014 documents a gatekeeper tier that was decided by hand, with checks left to an LLM that code could have made.
- Step 0.6 showed the existing pre-push checks fail open. Without `origin/HEAD`, `protectedBranches` or `.ai-framework.json`, branch protection, the diff-size check and the verify gate print a warning and let the push through (F14). A push to `main` succeeded in that state.
- Headless runs exit 0 even when the agent did nothing (F2), and tool names vary by model (F7), so neither the exit code nor the agent's own report can serve as proof.

## Options considered

- **Option A: keep the gatekeeper LLM as the main verifier of all checklist items.** One place, no new code. But it asks an LLM for facts, which is the DEC-014 failure, and costs tokens on every run.
- **Option B: keep the hooks as they are and only add warnings.** Cheapest. Step 0.6 shows warnings are not enough, because the push to `main` went through.
- **Option C: check every fact in code, with checks that fail closed, and leave only judgment to LLMs.** More code to maintain, but the result is repeatable. Chosen.

## Decision

Anything checkable in code is checked in code. LLMs judge.

1. **Facts are produced by code:** build and test results, branch, diff size, dependency manifest changes, protected-path changes, schema validity, loop limits.
2. **Judgments are made by LLMs:** whether a change has a bug, whether a plan is sound, whether a requirement is met.
3. **Checks fail closed.** When a check cannot decide (missing config, unknown base branch), it blocks with a readable reason. It never skips with a warning.
4. **Gates inspect the working tree**, not tool names and not what the agent reports.
5. **No LLM decides to stop or continue a loop.** The limit (`MAX_FIX_LOOPS`) and the stop reason are code.
6. **Headless preflight.** Before a headless run, the runner checks in code that `docs/project-overview/stack.md` has content and that `.ai-framework.json` exists. If not, it fails with a readable message ("run the first-run analysis interactively once"). There is no headless-specific `AGENTS.md`. (Decided 2026-10-03, see `docs/inventory.md`, section 4.)
7. **Human approval is made visible, not proven.** Code cannot prove a human approved a dependency change. The `dependency_change` check blocks the push unless the commit has a `Dependency-Approved:` trailer, which makes the approval reviewable.

Touches: `hooks/pre-push`, `hooks/build-verify.sh` and `agents/gatekeeper.md` (all split or moved in Phase 3A), a new `verification/` folder, the validator, and the runner preflight.

### Parity

The new path has parity with the current flow when it gives the same verification results and no regression in the baseline outcome. Same model, prompt count and reasoning are not required.

| Class | Metrics | Role in decisions |
|---|---|---|
| Hard requirement | Correctness and verification results; reliability (schema validity, no policy or permission violations) | Must hold |
| Optimization | Cost, latency | Trade-offs allowed if outcome and verification hold |
| Diagnostic | Review iterations | Informs, does not decide |

Comparison is per task, not by averages. A task with an "unknown" baseline value is excluded from that metric. A hard-requirement failure is a stop, whatever the optimization metrics show. The acceptable margin on the directional metrics is still open (decision #5 in the plan).

### To be completed

- **Gatekeeper classification (step 3A.1):** done 2026-11-03, see the table below.
- **Pipeline experiment outcome (after Phase 3C):** keep, replace with a declarative definition, or remove, with the evidence.
- **Soak verdict (step 4.5):** keep, extend or revert, based on 5 real PRs compared with the baseline.

### Gatekeeper classification (step 3A.1, 2026-11-03)

Every checklist item of `agents/gatekeeper.md`, labeled. "Decided by" names what decides the fact today. "3A.4" says what the trim does with the item.

| # | Item | Class | Decided by | 3A.4 |
|---|---|---|---|---|
| 1 | Lane: the diff matches the declared description | judgment | gatekeeper | keep |
| 2 | Lane: the diff delivers the description and the tests pass | judgment (the test part is row 20) | gatekeeper | keep |
| 3 | Lane: `quick-lane-check.py` STATUS OK, no manifest, lockfile or `.ai-framework.json` in the diff | deterministic | `quick_lane` check at push (commits with the `Lane: quick` trailer) | trim |
| 4 | Atomicity: matches exactly one row of the PR breakdown | judgment | gatekeeper | keep |
| 5 | Atomicity: one concern, no mixed scope | judgment | gatekeeper | keep |
| 6 | Atomicity: no refactor bundled with a feature | judgment | gatekeeper | keep |
| 7 | Atomicity: no FE and BE in one PR unless the architect justified it | judgment (open: path globs per project) | gatekeeper | keep |
| 8 | Atomicity: no unapproved dependency update bundled | deterministic | `dependency_change` at push | trim |
| 9 | Atomicity: independently revertable | judgment | gatekeeper | keep |
| 10 | Spec: implementation matches the confirmed spec | judgment | gatekeeper | keep |
| 11 | Spec: all acceptance criteria satisfied | judgment | gatekeeper | keep |
| 12 | Spec: nothing out of scope implemented | judgment | gatekeeper | keep |
| 13 | Branch: a feature branch with the correct prefix | deterministic | `pre-commit` hook (it allows 7 prefixes; the gatekeeper lists 5, without `hotfix/` and `release/`) | trim |
| 14 | Branch: no changes on `main` or `master` | deterministic | `pre-commit` (no direct commits) and `branch_protection` at push | trim |
| 15 | Lint scan reported zero violations | deterministic | `build-verify` lint at push, only where `.ai-framework.json` has the command | trim once `build-verify` blocks without config |
| 16 | Xray scan: zero issues with CVSS 8 or higher | deterministic | no code (the scan is run by `code-reviewer`) | keep, no code yet |
| 17 | Xray blocker resolved and the scan rerun clean | deterministic | no code | keep, no code yet |
| 18 | Xray warnings are present in the report | deterministic, informational (never blocks) | no code | candidate to drop |
| 19 | `code-reviewer` last verdict was APPROVE | deterministic once the report is a stored artifact | no code: the verdict exists only in the session | keep until the runner stores it |
| 20 | `qa` last run reported zero failures | deterministic | `build-verify` test at push, only where configured | trim with row 15 |
| 21 | Coverage did not decrease | deterministic | no code (needs a coverage command and a stored baseline) | keep, open |
| 22 | No dependency change without documented approval | deterministic (approval is made visible, not proven: point 7) | `dependency_change` at push | trim |
| 23 | `docs/` updated when a flow, the architecture, an API or an integration changed | judgment (whether the trigger applies) | gatekeeper | keep |
| 24 | Memory: check for new patterns, conventions or facts | judgment | gatekeeper | keep |
| 25 | Memory: report proposed updates instead of writing them | judgment | gatekeeper | keep |
| 26 | Memory: each proposal cites the file and line | judgment (format only) | gatekeeper | keep |
| 27 | Memory: the gatekeeper does not modify files | deterministic | the agent's `edit: deny` and `write: deny` | drop from the checklist |

Totals: 14 judgment, 13 deterministic. Of the 13, rows 3, 8, 13, 14, 22 and 27 are decided by code unconditionally, rows 15 and 20 only where `.ai-framework.json` configures the commands, and rows 16 to 19 and 21 by no code yet.

Notes for 3A.4:

- The gatekeeper's bash is limited to `git status`, `git log` and `git diff`, so rows 15 to 21 only read what other agents reported. Point 4 (inspect the tree, not the report) is not met for them.
- `build-verify` skips with a warning when `.ai-framework.json` is missing (F14), which point 3 forbids. Rows 15 and 20 can be trimmed only after that is changed.
- Trimmed checks now fail at push, after the gatekeeper has reported. The orchestrator has to treat a blocked push as a failed gate.
- Rows 16 to 19 and 21 stay in the gatekeeper until code decides them.

## Reasoning

1. **Agent or deterministic?** Facts are deterministic: the same input, run twice, gives the same answer by inspecting existing state, which is the rule of thumb in this folder's README. Judgment stays with agents. This DEC applies the README's rule to the whole verification layer.
2. **Trade-offs.** More code under `verification/`, with one passing and one failing fixture per check. Checks that used to warn now block, so repos without `.ai-framework.json` get friction until the first-run analysis has run. In return, the gatekeeper tier may shrink, which saves tokens.
3. **Cheaper way?** Warnings only (Option B) is cheaper and was shown not to work. Phase 1 of the plan, with no runner at all, already rejects the DEC-014 incident types, so this DEC does not depend on the runner.
4. **What a developer can now see or do.** A blocked push explains what is missing and how to fix it. A headless run that cannot work stops early with a message instead of hanging on a question nobody can answer.

## Consequences

- The hooks become thin entrypoints that call `verification/`.
- The gatekeeper is trimmed to judgment-only items in step 3A.4, and the tier may be dropped.
- `hooks/pre-push` needs a fail-closed rewrite of branch protection, diff size and the verify gate.
- Server-side branch protection on the remote stays required, because a client-side hook can always be skipped.
- Evidence: `tests/bench/permissions-evidence.md` (step 0.5), `tests/bench/git-permissions-evidence.md` (step 0.6), and findings F2, F7, F13 and F14 in `docs/transition-plan.md`.
