# Decision: Add a CRAP score gate as a new skill, built on static-code-analysis's existing
# complexity and coverage data

**Date:** 2026-08-05
**Status:** accepted

## Context
`static-code-analysis` already computes cyclomatic complexity (lizard, CCN threshold) and
changed-line coverage independently, gating each against its own threshold. It never
combines them. A function can be high-complexity-but-well-tested (probably fine) or
low-complexity-but-untested (usually fine), but the combination — high complexity AND low
coverage on the same function — is a specific, sharper risk signal that two independent
thresholds don't capture on their own.

CRAP (Change Risk Anti-Pattern): `CRAP(m) = complexity(m)^2 * (1 - coverage(m)/100)^3 +
complexity(m)`. Purely arithmetic over data `static-code-analysis` already produces — no
new tool, no agent judgment to compute it.

## Options considered
- A: Fold the CRAP calculation directly into `static-code-analysis` — rejected: that skill
     is already doing two distinct jobs (complexity gate, duplication gate); adding a third
     combined metric with its own threshold and its own remediation flow bloats one file
     past what matches ai-framework's existing convention of small, focused skills (see
     the granularity of the `clean-code-*` skill family)
- B: New skill, `crap-score`, run after `static-code-analysis`, consuming its output —
     chosen, matches the existing convention

## Decision: Option B
New skill `skills/crap-score/SKILL.md`. Runs after `static-code-analysis` in the review
pipeline, reusing its complexity output and the project's coverage report rather than
re-computing either. On a threshold breach, it does not auto-refactor — it reports the
specific score and function, then the decision (refactor now vs. accept and proceed) is the
developer's, made the same way any other `ask`-permissioned decision is made in this
framework: surfaced in-session, not silently auto-resolved.

## Reasoning
1. Agent or deterministic? Fully deterministic — the formula has zero ambiguity once
   complexity and coverage numbers exist. The *decision* on a breach (refactor vs. accept)
   is correctly left to the developer, not automated, consistent with how `plan-reviewer`
   and `code-reviewer` already surface judgment calls rather than resolving them silently.
2. Trade-off: adds one more gate to the review pipeline; justified because it's the only
   gate here measuring *combined* risk rather than either dimension alone, and it's nearly
   free to compute given the inputs already exist.
3. Cheaper alternative: none simpler — reusing existing tool output rather than adding a new
   tool is already the cheapest version of this.
4. Visibility gained: a single, prioritized risk ranking per function, rather than needing
   to mentally cross-reference two separate threshold reports to spot the dangerous
   intersection.

## Consequences
- `skills/crap-score/SKILL.md` added; runs as a precheck stage after `static-code-analysis`,
  same position in the pipeline that skill already occupies relative to `code-reviewer`.
- Threshold is configurable per project, not hardcoded — "risky" reasonably differs by
  codebase maturity.
- If a project doesn't have coverage infrastructure configured, this gate is skipped and
  reported as unavailable, matching `static-code-analysis`'s existing "coverage
  infrastructure missing → record as unavailable, continue" behavior — not treated as a
  failure.