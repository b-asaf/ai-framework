# DEC-017 — Developer control points and autonomous git

**Status:** Accepted
**Date:** 2026-10-12

## Context

- The goal is to let the framework read files, edit files, create branches, commit, push through the draft script and open draft PRs/MRs with fewer questions, while the developer keeps the decisions that matter.
- The flow already has two real checkpoints. `@product-manager` grills the developer (`grill-me`) until the spec is confirmed. `@architect` grills the solution, `@plan-reviewer` checks the HLD, and the developer approves the atomic PR breakdown (orchestrator Steps 1 to 3).
- On top of that, `AGENTS.md` rule 5 asked for a plan confirmation before every write, and the implementers waited for a confirmation and asked the developer to create branches.
- Findings from the hardening work: F9 (a catch-all placed last turned the git allows into prompts), F13 (a headless run auto-rejects a prompt), F8 (headless runs stop at the plan-confirmation gate), and F20 (an agent's own `"*"` rule overrides all global rules before it, so the global denies do not protect the orchestrator).

## Options considered

- **Option A: keep a confirmation before every write.** The developer sees everything, but the plan is asked about twice, after the spec and plan checkpoints have already approved it. It also blocks headless runs (F8).
- **Option B: remove every confirmation and involve the developer only at the end.** The cheapest in questions, but it removes the checkpoints where the developer's intent enters.
- **Option C: a fast lane for small fixes that skips the product-manager and the architect.** Rejected for now. Whether a change is small is a fact, and an agent deciding it up front is judgment where code should decide (DEC-015). Revisit it as a developer-declared lane checked afterwards by the diff-size gate.
- **Option D: two approval checkpoints and three control points, with everything else autonomous and the limits set by deterministic denies.** Chosen.

## Decision

**Approval checkpoints** (the developer is present in both):

1. The confirmed spec: `@product-manager`, using `grill-me`.
2. The HLD with its atomic PR breakdown: `@architect`, checked by `@plan-reviewer`.

After checkpoint 2 the framework executes without asking again. Implementation agents write files within the current PR row. The orchestrator creates branches, runs `git add .` and `git commit`, and runs `scripts/open-draft-pr.py`, which pushes and opens the draft PR/MR. Anything outside the approved PR row halts.

**The developer keeps three control points:**

1. **Publishing.** Changing a PR/MR from draft to ready, and merging, stay manual. No agent has a command for them: `gh pr ready`, `gh pr merge`, `gh pr create`, `glab mr merge` and `glab mr create` are denied in the global config and in every agent that can commit.
2. **Third-party changes.** Adding, removing or updating a dependency needs the developer's approval, as `third-party-policy` and `AGENTS.md` rule 3 already say. Edits to manifests and lockfiles stay `ask` in the implementers, and package-manager commands stay `ask` (auto-rejected in a headless run).
3. **A new task on an existing branch.** When the current branch is not the base branch, the orchestrator asks once, before the spec grill: stay on it, open a new branch from it, or open a new branch from the base branch. On the base branch it creates the branch without asking. The next PR in a breakdown asks where its branch starts.

**Permissions:**

- The global `opencode.json` has the catch-all first, then the git allows, then the denies.
- The orchestrator is the only agent that commits. Its own block repeats the denies, adding `--no-verify` and branch deletion, because its own `"*"` rule overrides the global ones. Pushing is script-only.
- The validator enforces both (`lint_opencode_config`, `lint_commit_agents`).

Touches: `opencode.json`, `AGENTS.md` (check 2 and rule 5), `agents/orchestrator.md`, the six implementer agents, `tools/validate_framework.py`, and section 6 of `docs/transition-plan.md`.

## Reasoning

1. **Agent or deterministic?** The trigger for the branch question is deterministic: the current branch compared with the base branch. The spec and plan checkpoints are conversations between an agent and the developer. The publishing limits and the commit limits are permissions, so code enforces them and no agent has to remember them.
2. **Trade-offs.** More is decided in the two checkpoints, and less is asked afterwards. The denies cost flexibility: agents other than the orchestrator cannot commit, and no agent can delete a branch.
3. **Cheaper way?** Option B is cheaper, but the developer then loses the points where intent enters.
4. **What a developer can now see or do.** A draft PR appears without any prompt after the gatekeeper passes. A new task on a feature branch asks where to branch. Headless runs no longer stop at the plan-confirmation gate once a PR breakdown is approved.

## Consequences

- In multi-repo tasks the orchestrator still tells the developer which branch to create in the other repos, because it cannot run git there. Deferred.
- `git commit -n` is not covered by the `--no-verify` deny. The pre-push gate still runs through the script.
- A fast lane is deferred. The trigger is that running the full flow for trivial changes becomes a real cost.
- Step 3A adds deterministic backstops: a `dependency_change` check and a fail-closed `branch_protection` check.
- Evidence: `tests/bench/git-autonomy-evidence.md`, and findings F9, F13, F19 and F20 in `docs/transition-plan.md`.
