# DEC-018 — Fast lane for quick fixes, declared by the developer

**Status:** Accepted
**Date:** 2026-10-12

## Context

- DEC-017 set two approval checkpoints (the spec with `@product-manager`, the HLD with its PR breakdown with `@architect` and `@plan-reviewer`) and left everything after them autonomous.
- Every task starts at the orchestrator and goes through both checkpoints. For a one-line fix this is a lot of ceremony: a spec grill, an HLD, an independent plan review and a PR table around a change the developer could describe in a sentence.
- DEC-017 rejected a fast lane that an agent decides on (its Option C), because whether a change is small is a fact, and an agent judging it up front is judgment where code should decide (DEC-015). It said to revisit a lane that the developer declares, with code checking it afterwards.
- The pre-push diff-size backstop (DEC-007, DEC-009) already exists, but it measures lines only (default 400), runs at push time, and skips itself when it cannot find a base branch (F14).

## Options considered

- **Option A: no fast lane.** One path for every task. Simple, but small fixes pay the full cost.
- **Option B: the orchestrator decides what is small.** Rejected in DEC-017.
- **Option C: the developer declares a quick fix with `/quick`, a script measures the change, and every review, test and gate step still runs.** Chosen.
- **Option D: a fast lane that also skips QA or the gatekeeper.** Rejected. The independent validation of an implementer's work (cross-family) is a framework rule, and the quick lane skips thinking before the work, not checking after it.

## Decision

**Declaration.** Only the developer declares the lane, with the command `/quick <description>` (`commands/quick.md`). No agent may choose it, offer it as a shortcut or infer it from a request that sounds small. The description is the whole spec.

**What the lane skips:** the spec grill (`@product-manager`), the HLD (`@architect`), the plan review (`@plan-reviewer`), and the PR breakdown.

**What it keeps:**
- the branch check (DEC-017 control point 3);
- a two-line plan, stated without waiting;
- one implementation agent, with its scope limited to the description;
- `@code-reviewer`, `@qa` and `@gatekeeper`, including the cross-family independence rules;
- the final task summary, with the line `Lane: quick`;
- the commit, the script push and the draft PR, with a `Lane: quick` trailer paragraph in the commit message;
- all of the developer's control points (publishing, third parties, existing branch).

**Limits, measured by code.** `scripts/quick-lane-check.py` compares the uncommitted change with `HEAD`, and counts untracked files too. The lane ends when the change touches **more than 3 files or more than 60 changed lines** (added plus deleted, ignoring whitespace-only changes), or touches a manifest, a lockfile or `.ai-framework.json`. The limits default to 3 and 60, and `.ai-framework.json` may set `quickLane.maxFiles` and `quickLane.maxLines`. The script checks that the working tree is clean before the fix starts (`--start`).

**Over the limit.** The orchestrator stops, tells the developer "This is no longer a quick fix: <reason>", and offers the regular lane (`/task`) or a split. It never continues on its own and never trims the change to fit.

**The gatekeeper.** When the summary says `Lane: quick`, the checklist items about the architect's PR breakdown and the product-manager's spec are replaced by "matches the declared description and nothing more", and the summary must show `STATUS: OK` from the script. Nothing else is relaxed.

Touches: `commands/quick.md` (new), `scripts/quick-lane-check.py` (new), `agents/orchestrator.md`, `agents/gatekeeper.md`, `AGENTS.md` (rule 5), section 6 and step 3A.2 of `docs/transition-plan.md`.

## Reasoning

1. **Agent or deterministic?** The declaration is the developer's decision. Measuring the change is deterministic, so a script does it, as `open-draft-pr.py` does for the PR. The agent only reads the script's `STATUS:` line.
2. **Trade-offs.** A quick fix skips the independent plan review, so a wrong approach is caught by the code review and QA instead of the plan. The limits keep that risk small, and the developer chooses it knowingly. The measuring script is one more file to maintain.
3. **Cheaper way?** Making the pre-push diff-size check stricter would be cheaper, but it runs only at push time, after the work is done, and it skips itself when it cannot find a base branch.
4. **What a developer can now see or do.** Type `/quick fix the off-by-one in the pager` and get a branch, an implementation, a review, tests, a gate and a draft PR with no spec or design conversation. If the change grows, the lane stops and asks.

## Consequences

- The commit trailer `Lane: quick` makes quick fixes findable: `git log --grep "Lane: quick"`.
- A model could claim `Lane: quick` for a regular task. The command is the only entry, the orchestrator is told never to declare it, and the script's limits apply either way. Step 3A adds a deterministic push-time check: a commit with the trailer that exceeds the limits is blocked.
- A quick fix that needs a dependency change leaves the lane: the manifest check makes it over the limit, so the regular lane's third-party approval applies.
- The limits are a starting point. If they feel wrong after real use, change them in `.ai-framework.json` or in the script's defaults.
- Evidence: `tests/test_quick_lane_check.py` (the measuring script on real temporary git repos) and `tests/test_fast_lane.py` (the wording guards).
