# DEC-015: Deterministic verification

Status: Accepted (principle). Sections 4 to 6 are completed in steps 3A.1, 3C and 4.5.
Date: 2026-10-06
Related: DEC-014, DEC-016, `docs/transition-plan.md`, `docs/inventory.md`

## 1. Context

- DEC-014 documents a gatekeeper tier that was decided by hand, with checks left to an LLM that could have been done by code.
- Step 0.6 showed the existing pre-push checks fail open. Without `origin/HEAD`, `protectedBranches` or `.ai-framework.json`, branch protection, the diff-size check and the verify gate print a warning and let the push through (F14). A push to `main` succeeded in that state.
- Headless runs exit 0 even when the agent did nothing (F2), and tool names vary by model (F7), so neither the exit code nor the agent's own report can serve as proof.

## 2. Decision

**Anything checkable in code is checked in code. LLMs judge.**

1. **Facts are produced by code:** build and test results, branch, diff size, dependency manifest changes, protected-path changes, schema validity, loop limits.
2. **Judgments are made by LLMs:** whether a change has a bug, whether a plan is sound, whether a requirement is met.
3. **Checks fail closed.** When a check cannot decide (missing config, unknown base branch), it blocks with a readable reason. It never skips with a warning.
4. **Gates inspect the working tree**, not tool names and not what the agent reports.
5. **No LLM decides to stop or continue a loop.** The limit (`MAX_FIX_LOOPS`) and the stop reason are code.
6. **Headless preflight.** Before a headless run, the runner checks in code that `docs/project-overview/stack.md` has content and that `.ai-framework.json` exists. If not, it fails with a readable message ("run the first-run analysis interactively once"). There is no headless-specific `AGENTS.md`. (Decided 2026-10-03, see `docs/inventory.md`, section 4.)
7. **Human approval is made visible, not proven.** Code cannot prove a human approved a dependency change. The `dependency_change` check blocks the push unless the commit has a `Dependency-Approved:` trailer, which makes the approval reviewable.

## 3. Parity

The new path has parity with the current flow when it gives the same verification results and no regression in the baseline outcome. Same model, prompt count and reasoning are not required.

| Class | Metrics | Role in decisions |
|---|---|---|
| Hard requirement | Correctness and verification results; reliability (schema validity, no policy or permission violations) | Must hold |
| Optimization | Cost, latency | Trade-offs allowed if outcome and verification hold |
| Diagnostic | Review iterations | Informs, does not decide |

Comparison is per task, not by averages. A task with an "unknown" baseline value is excluded from that metric. A hard-requirement failure is a stop, whatever the optimization metrics show.

Open: the acceptable margin on the directional metrics for the Phase 2 gate (decision #5).

## 4. Gatekeeper classification

To be completed in step 3A.1: every gatekeeper checklist item labeled deterministic or judgment.

## 5. Pipeline experiment outcome

To be completed after Phase 3C: keep, replace with a declarative definition, or remove, with the evidence.

## 6. Soak verdict

To be completed in step 4.5: keep, extend or revert, based on 5 real PRs compared with the baseline.

## 7. Consequences

- More code to maintain under `verification/`, with one passing and one failing fixture per check. The hooks become thin entrypoints.
- Checks that used to warn now block. Repos without `.ai-framework.json` get friction until the first-run analysis has run, so the message must say exactly what to do.
- The gatekeeper tier may shrink or go away once its deterministic items move to code.
- Server-side branch protection stays required, because a client-side hook can always be skipped.

## 8. Evidence

- `tests/bench/permissions-evidence.md` (step 0.5)
- `tests/bench/git-permissions-evidence.md` (step 0.6)
- Findings F2, F7, F13 and F14 in `docs/transition-plan.md`
