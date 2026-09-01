# DEC-011 — Model Catalog Drift Fix (claude-sonnet-4.6 → claude-sonnet-5)

**Status:** Accepted
**Date:** 2026-09-01

## Context

MODEL-ASSIGNMENT-MATRIX.md was last verified against live `opencode models`
output on 2026-08-30. By 2026-09-01, the Copilot entitlement had changed:
`github-copilot/claude-sonnet-4.6` was no longer present in the live
catalog. Nothing in the framework detected this automatically — the first
signal was a headless `/review` run failing with:

    ProviderModelNotFoundError: Model not found: github-copilot/claude-sonnet-4.6

This affected:
- Global user config: `~/.config/opencode/opencode.json`
- Repo config: `ai-framework/opencode.json`
- 8 of 15 agent frontmatter files (all MID-tier, per the matrix):
  orchestrator, product-manager, backend, frontend, ui, db, api,
  frontend-error-fixer

A related but distinct issue was found during diagnosis: `README.md` and
`docs/session-summary.md` additionally contained stale hyphenated IDs
(`claude-opus-4-8`, `claude-haiku-4-5`) that never matched the live catalog
format at all — separate from this drift, likely predating DEC-011's
original agent-frontmatter fix and missed because verification at the time
checked only for absence of the old `anthropic/*` namespace, not for
validity of the model-version segment.

## Options considered

1. **Manual fix only** — correct the current drift, no process change.
2. **Manual fix + deterministic validation script** (already scoped in
   MODEL-ASSIGNMENT-MATRIX.md section 5/8, referenced as an outstanding
   DEC-011 item in prior session handoff) — catches this class of drift
   automatically at session/task start going forward.

## Decision

Apply the manual fix now (this DEC). Deterministic validation remains a
tracked, not-yet-built follow-up — this session's failure is a concrete,
reproduced example of exactly the gap that validation script is meant to
close, and should raise its priority.

## Fix applied

- `github-copilot/claude-sonnet-4.6` → `github-copilot/claude-sonnet-5`
  in: global opencode.json, repo opencode.json, and all 8 affected
  agent files.
- MODEL-ASSIGNMENT-MATRIX.md catalog table and section 2 assignments
  updated to match.
- README.md / session-summary.md model tier tables corrected (separate
  stale-format issue, fixed alongside).

## Test evidence

- Prior to fix: `opencode run --command review` failed 3x with
  `ProviderModelNotFoundError` (session model + two mis-guessed
  replacement attempts: `anthropic/claude-sonnet-4-6`, then
  `github-copilot/claude-sonnet-4-6` — wrong version, not just wrong
  namespace).
- After fix: 3 consecutive headless `/review` runs against
  `D:\BTA\bta-frontend` show no `ProviderModelNotFoundError` in debug
  logs. Session-level model resolution confirmed clean.
- **Not yet confirmed:** agent-level resolution for the 8 corrected
  files, since an unrelated permission/bash-chaining bug (logged
  separately) stops the pipeline before routing reaches those agents.
  This is an open gap — full pipeline dispatch through all agent tiers
  is still unverified end-to-end.

## Consequences

- Live model catalogs drift independently of framework intent (per
  matrix section 8) and currently do so silently. This session is
  direct evidence: correct on 2026-08-30, broken by 2026-09-01, only
  caught because a run happened to fail.
- Deterministic validation (matrix section 5, `setup.py --verify`
  wiring, task-start pre-flight) remains the durable fix and should be
  prioritized next, ahead of further manual feature work on DEC-011's
  original cross-family scope.