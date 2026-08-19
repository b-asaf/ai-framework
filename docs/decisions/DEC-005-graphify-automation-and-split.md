# Decision: Automate graphify wiring in first-run-analysis; split graphify SKILL.md into references/

**Date:** 2026-08-18
**Status:** accepted

## Context
Two gaps found through direct use, not design review:

1. `first-run-analysis` Step 7 built the initial graph but never ran `graphify <platform>
   install` or `graphify hook install` — confirmed by re-reading Step 7's actual text. This
   meant every new project got a graph that was never automatically consulted (no nudge) and
   never automatically kept fresh (no rebuild hook) unless a developer separately remembered
   `SKILL.md`'s "Staying in sync" section and ran it by hand.
2. `graphify/SKILL.md` is one of the longest skill files in the framework and loads in full
   whenever triggered (by `zoom-out`, `first-run-analysis`, or `pattern-enforcement`) — unlike
   `first-run-analysis`, which already keeps heavy detail in `references/*.md`, loaded only
   when that specific step needs it.

## Decision
1. `first-run-analysis` Step 7's `graphify-out/` bullet now includes running the install and
   hook-install commands as steps 2–3 of that bullet, before the commit step — full wiring
   happens automatically on first run, not as a separate manual step.
2. `graphify/SKILL.md` is split: the main file keeps only "Quick reference" and "When to use
   it instead of Read/Glob/grep" — the two sections needed on essentially every load. Five
   sections move to `references/`, loaded only when the specific task needs them:
   `building-and-refreshing.md`, `multi-repo.md`, `visualization.md`, `staying-in-sync.md`,
   `relationship-to-skills.md`.

## Reasoning
1. Agent or deterministic? Both fixes are deterministic — Step 7 now runs a fixed command
   sequence rather than relying on a developer to remember a separate manual step; the
   reference split is a fixed content-loading structure, not a judgment call.
2. Trade-off: none identified for the Step 7 fix. For the split, a task needing several
   reference sections at once now costs the same total tokens as before, spread across more
   tool calls rather than one — acceptable, since most tasks need at most one or two of the
   five sections, not all of them.
3. Cheaper alternative: none simpler — this directly reduces the common-case token cost
   (Context Discipline, principle #7 from the source project's process) without losing any
   content, only its default-loaded status.
4. Visibility gained: a new project onboarded after this fix gets fully working graphify
   (graph + nudge + hooks) from one `/first-run` pass, with nothing left implicit.

## Consequences
- Any project already populated before this fix (e.g. `garud-backend`, `bta-backend`) does
  not retroactively get the nudge/hooks — the manual commands documented in
  `references/staying-in-sync.md`'s "If a project predates the DEC-005 automation" section
  still apply to those until run once by hand.
- Future skill files this large should default to the `references/` pattern from the start,
  matching `first-run-analysis`'s existing convention, rather than being split after the
  fact.