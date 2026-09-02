# Decision: Deterministic diff-size backstop for atomic-changes, added to pre-push

**Date:** 2026-08-18
**Status:** accepted (base-branch detection significantly extended by DEC-009)

## Context
`atomic-changes` states a threshold ("~400 lines of meaningful change") and a full agentic
enforcement chain (architect defines the breakdown, orchestrator tracks it, code-reviewer
flags violations, gatekeeper gates it) — confirmed by reading the skill directly. No
deterministic check anywhere measured an actual diff against that threshold. This is the
same category of gap `build-verify`'s hook already exists to close for tests/lint (agentic
loop backed by a hook that runs outside any agent's control) — atomic-changes had the
agentic half without the hook half.

## Options considered
- A: Leave enforcement entirely agentic — rejected, same reasoning `build-verify` already
     rejected this for: an agent could misjudge, skip, or misreport it
- B: New, separate git hook dedicated to diff size — rejected: `pre-push` already exists as
     the "structural backstop beyond agent self-report" pattern; a second hook duplicates
     infrastructure for a check that fits naturally alongside build-verify's own gate
- C: Add the check directly into the existing `pre-push` hook, before build-verify runs —
     chosen

## Decision: Option C
`hooks/pre-push` computes the actual diff size and compares it against a configurable
`maxDiffLines` in `.ai-framework.json`, defaulting to atomic-changes' own documented ~400
lines if not configured. Blocks the push with a clear message if exceeded. Escape hatch
`SKIP_DIFF_SIZE_CHECK=1`, separate from `SKIP_BUILD_VERIFY=1` so either can be overridden
independently.

`skills/atomic-changes/SKILL.md` updated to document this as the deterministic backstop
beneath its otherwise fully agentic enforcement chain.

## Reasoning
1. Agent or deterministic? Fully deterministic — diff size is exact, not estimated or
   agent-judged. This was the entire point: atomic-changes had a stated threshold with zero
   deterministic enforcement anywhere.
2. Trade-off: none identified — reuses existing hook infrastructure rather than adding new
   moving parts.
3. Cheaper alternative: Option A (status quo) is cheapest to build but doesn't actually
   close the gap; Option C costs a few lines added to an already-existing, already-trusted
   script.
4. Visibility gained: a genuinely oversized push now gets a specific, actionable message
   instead of relying entirely on an agent having caught it earlier in the chain.

## Consequences
- `.ai-framework.json` gains an optional `maxDiffLines` key; absence falls back to 400.
- This does not replace the agentic PR-breakdown process — a well-planned breakdown should
  rarely trigger this hook.
- **Significantly extended by DEC-009**: this entry's original base-branch selection (first
  matching protected branch) and raw `git diff --shortstat` line counting were both found
  to have real gaps during smoke testing on a real repo —
  see DEC-009 for the corrected, more rigorous mechanism (explicit config or unambiguous
  git reflog evidence for the diff base; meaningful-line filtering to exclude
  whitespace/import/rename noise). This entry's core decision (the backstop belongs in
  `pre-push`, configurable threshold, escape hatch) stands.
