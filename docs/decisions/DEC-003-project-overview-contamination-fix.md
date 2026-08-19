# Decision: Fix project-overview cross-project contamination bug

**Date:** 2026-08-11
**Status:** accepted

## Context
Running `/first-run` in real project populated `skills/project-overview/` (SKILL.md's
status line, and all five `sub/*.md` files) with real, project-specific data — inside the
shared `ai-framework` repo itself, not inside real project's own repo. Since
`skills/project-overview/` is wired globally via `setup.py`'s directory-level symlink/
junction (`~/.config/opencode/skills` -> `ai-framework/skills`), this data becomes visible
to every project opened through this install, not just real project. Confirmed by direct
inspection: `SKILL.md`'s Status line read "POPULATED... (real project monorepo)," and every
`sub/*.md` file contained real real projects stack, topology, pattern, and tooling details.

Root cause: `first-run-analysis`'s Step 7 instruction for `.ai-framework.json` explicitly
says "write to the root of each individual repo... not the shared skills location." The
instruction for `project-overview`, immediately below it, has no equivalent clause — it was
architecturally incomplete, and the agent followed it literally.

Scope check: `opencode.json` and `.opencode/opencode.json` (the actual global agent config)
were confirmed clean of any real project references. Git hooks were confirmed to never be
committed into any project repo — `setup.py`'s `add_git_template()` only sets
`git config --global init.templateDir`, a machine-local setting; hooks land in each
developer's own untracked `.git/hooks/` on `git init`/`git clone`, never in tracked files.
So non-ai-framework teammates on a shared project are unaffected by this bug or by the
framework's hooks in general — the contamination was fully contained to the shared
`project-overview` skill content.

## Decision
1. Real project-overview data is relocated to `docs/project-overview/`
   inside its own repo (matching the already-established pattern of `docs/refactoring-
   plan.md` and `.ai-framework.json` living in that project's own `docs/`).
2. The shared `ai-framework` copy (`skills/project-overview/SKILL.md` and all five
   `sub/*.md` files) is reset to its clean, unpopulated `[XXX]` template state.
3. `first-run-analysis`'s Step 7 instruction is corrected with an explicit location clause
   for `project-overview`, matching `.ai-framework.json`'s existing pattern, plus a new
   standing check: if the shared `SKILL.md`'s Status line ever shows a populated project
   name, stop and treat it as a sign this bug has recurred.

## Reasoning
1. Agent or deterministic? The underlying fix is deterministic — a corrected instruction
   with an explicit, unambiguous target location, not something requiring agent judgment
   to get right. The bug existed specifically because the instruction *lacked* that
   determinism.
2. Trade-off: none identified — this is a straightforward correctness fix with no
   competing concern.
3. Cheaper alternative: none simpler than fixing the instruction at its source; a workaround
   at the project level would leave the bug live for the next project's first `/first-run`.
4. Visibility gained: the new standing check turns a silent, hard-to-detect failure mode
   (wrong data silently loaded into an unrelated project) into an immediately visible one.

## Consequences
- Every project that has already run `/first-run` before this fix should be checked for the
  same contamination pattern, not assumed clean.
- `first-run-analysis`'s own documentation (and any onboarding notes referencing it) should
  point to this decision as the reason the location clause exists, so it isn't accidentally
  removed later as "redundant" with the `.ai-framework.json` clause above it.
- This is now a concrete example for what "detect, never assume" means in this framework's
  own decision-log process (`docs/decisions/README.md`) — worth referencing directly if that
  README is ever revised.