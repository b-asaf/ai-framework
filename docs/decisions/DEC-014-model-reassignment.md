# DEC-014 — Model Reassignment: refactor-planner fix, code-reviewer, gatekeeper

**Status:** Accepted
**Date:** 2026-09-29

## Context

A manual update of the model catalog and agent frontmatter (bringing the
matrix in line with a new live `opencode models` list) introduced one bug
and one policy violation, and a separate conversation about this
framework's git-permission automation changed the stakes of a third
assignment enough to warrant revisiting it.

1. **Bug:** `refactor-planner` was manually set to
   `github-copilot/claude-opus-5.5` — the exact same model already assigned
   to `plan-reviewer`. `refactor-planner`'s plans are required to be
   independently validated by `plan-reviewer` (Model Assignment Matrix
   section 3). Same-model "validation" is not independent; it shares
   whatever blind spots the model has. This was very likely a copy/paste
   mix-up between two planning-adjacent agents during the manual edit.

2. **Policy violation:** `code-reviewer` was assigned
   `github-copilot/gpt-6-sol`, which the matrix's own section 7 lists as
   experimental — "evaluate before default assignment." No such evaluation
   was recorded. The assignment was live but ungoverned.

3. **Reconsideration:** `gatekeeper` was on `claude-haiku-4.5`, the
   catalog's lightest tier. That was a reasonable cost/latency choice when
   a PASS from gatekeeper still led to a human manually reviewing the diff
   and running `git add`/`commit`/`push`/opening the PR themselves. In this
   same session, `AGENTS.md` Check 4 was changed so that a gatekeeper PASS
   now triggers an automatic `git push` and an automatically-opened draft
   PR/MR, with no human approval step in between. Gatekeeper's checklist
   (see `agents/gatekeeper.md`) is genuinely a verification/aggregation
   task, not open-ended code review — but it now includes judgment calls
   (e.g. "no FE + BE mixed unless architect-justified," matching the diff
   against the PR breakdown) whose failure mode changed from "a human
   catches it a minute later" to "a draft PR is already open before anyone
   looks."

## Options considered

**For `code-reviewer`:** (a) formally promote `gpt-6-sol` with a recorded
evaluation, or (b) move to an already-appropriate non-experimental model.

**For `gatekeeper`:** (a) leave on `claude-haiku-4.5`, accepting the
increased consequence of a missed checklist item, or (b) upgrade to a
stronger tier, accepting the added cost/latency on every task's final step.

## Decision

- `refactor-planner`: `claude-opus-5.5` → `github-copilot/gpt-6-astra`
  (matches `architect` — both are GPT planning agents validated by the
  Claude `plan-reviewer`; restores the cross-family requirement).
- `code-reviewer`: `gpt-6-sol` → `github-copilot/gpt-5.6-terra` (option b —
  strong-tier, non-experimental, already GPT-family for the required
  cross-family check against Claude implementers, and deliberately a
  different specific model than `qa`'s `gpt-5.6-sol` rather than the same
  one reviewing twice). `gpt-6-sol` reverts to the section 7 experimental
  list; it may be promoted later with its own evaluation record.
- `gatekeeper`: `claude-haiku-4.5` → `github-copilot/claude-sonnet-5`
  (option b — same tier as the implementers it's indirectly gating, still
  Claude family so the `code-reviewer`/`qa` → `gatekeeper` cross-family
  edges hold, no change to its read-only permissions or checklist scope).

## Fix applied

- `agents/refactor-planner.md`, `agents/architect.md`: confirmed/set to
  `github-copilot/gpt-6-astra`.
- `agents/plan-reviewer.md`: confirmed `github-copilot/claude-opus-5.5`.
- `agents/code-reviewer.md`: `github-copilot/gpt-5.6-terra`.
- `agents/qa.md`: confirmed `github-copilot/gpt-5.6-sol`.
- `agents/gatekeeper.md`: `github-copilot/claude-sonnet-5`.
- `docs/decisions/MODEL-ASSIGNMENT-MATRIX.md` section 2 rows, section 7
  experimental list, and the catalog's "intended use" column updated to
  match. Status changed `Proposed` → `Accepted`. Verified-date bumped.
- `docs/session-summary.md` agent model tiers table corrected to match.

## Not done in this pass

- `tools/validate_agents.py` still does not check assignments against the
  live `opencode models` output (Model Assignment Matrix section 5, item
  3) — the exact gap that let DEC-011's drift go undetected. Tracked, not
  yet built.
- No implementer (`api`/`backend`/`db`/`frontend`/`frontend-error-fixer`/`ui`)
  was moved to `gpt-5.3-codex` (coding-specialized). The catalog explicitly
  flags it as needing deliberate evaluation first (section 7); this DEC
  doesn't constitute that evaluation.

## Test evidence

- `python tools/validate_agents.py .` — catalog membership, family
  labeling, and all 16 required cross-family validation edges checked
  clean after the reassignment (see the check run alongside this DEC).
