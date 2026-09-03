# DEC-012 — `/review` Pipeline Dispatch and Permission Fixes

**Status:** Accepted
**Date:** 2026-09-03
**Related:** DEC-011 (model catalog drift — separate root cause, fixed independently)

## Context

Following DEC-011's model-catalog fix, headless `opencode run --command
review` still failed to produce a working end-to-end pipeline. Diagnosis
surfaced six distinct, independent bugs, several masking each other —
fixing one revealed the next underneath. All were confirmed via real
headless runs against `real project`, using
`--print-logs --log-level DEBUG` throughout (plain `run --command` output
gives only an opaque `UnknownError` ref with no way to diagnose it).

## Bugs found and fixed

### 1. `/review` and `/task` had no `agent:` frontmatter field

`commands/review.md` and `commands/task.md` declared only `description:`,
with no `agent:` field. Per opencode's own command-frontmatter spec, this
means opencode selects its own built-in default primary agent (`build`)
rather than any framework-defined agent. Confirmed directly in debug logs:
`command=review agent=undefined` followed by
`stream ... agent=build mode=primary`.

Effect: neither command ever actually entered the framework's own
permission/routing system. `orchestrator.md`'s Check 1 (first-run),
Check 2 (branch guard), and all step-by-step routing logic never ran —
the generic `build` agent read the command body as prose with no
obligation to follow it. This is the most likely explanation for every
prior session's inability to get a clean `/review` dispatch, including
the originally-diagnosed `err_4e58218f`/`err_a4705590`/`err_c46d14fb`.

**Fix:** added `agent: orchestrator` to both `commands/review.md` and
`commands/task.md` frontmatter.

### 2. `orchestrator.md` had no review-only entry point

Adding `agent: orchestrator` to `/review` alone would have caused the
orchestrator to start at Step 1 (Clarify → `@product-manager`), since its
instructions describe one unconditional "on every task" flow with no
awareness of being entered for a review-only invocation.

**Fix:** added a new `## Invoked via /review — review-only entry point`
section to `orchestrator.md`, instructing it to enter directly at Step 6
(Lint & Review), run only Steps 6–9, report PASS/FAIL, and stop — skipping
Steps 1–5 (no spec/design needed for reviewing already-implemented work)
and Step 10 (branch/PR handoff, out of scope for a standalone review).

`commands/task.md` needed no equivalent change — its 8-step body already
matches `orchestrator.md`'s Steps 1–10 directly, so entering at the top is
correct as-is.

### 3. Permission rule ordering was backwards (framework-wide)

Per opencode's own docs: *"Rules are evaluated by pattern match, with the
last matching rule winning. A common pattern is to put the catch-all `*`
rule first, and more specific rules after it."* Every one of the 15 agent
files' `permission.bash` blocks did the opposite — catch-all `"*"` listed
**last**. Since `"*"` matches everything, and last-match-wins, the
catch-all was silently overriding every specific `allow`/`deny` rule
before it, in every agent, for both single and chained commands. Confirmed
directly: even an unchained `git status` — explicitly `allow`-listed — was
being evaluated against `"*"` (or, after a partial fix, against `"git *":
deny`, which had the same relative-ordering problem one level down).

This is very likely the true root cause underneath what was initially
suspected to be a command-chaining problem (see #4) — chained and
unchained commands were both failing, for the same reason, before any
chaining was involved.

**Fix (applied so far — orchestrator.md and code-reviewer.md only):**
reordered each file's `permission.bash` block broadest-to-narrowest,
top-to-bottom: `"*"` first, then `deny` rules, then `ask` rules, then the
specific `allow` rules last (so they win). Permission *semantics* are
unchanged — only ordering.

**Outstanding:** the same reordering has not yet been applied to the
remaining 13 agent files (`architect`, `api`, `backend`, `db`,
`frontend`, `frontend-error-fixer`, `gatekeeper`, `plan-reviewer`,
`product-manager`, `qa`, `refactor-planner`, `ui`,
`web-research-specialist`). Each likely has the identical bug, unverified
until fixed — should be treated as a known gap, not assumed safe by
extrapolation.

### 4. Command chaining defeats exact-string permission matching

Independent of #3: opencode's `bash` permission matcher evaluates each
distinct tool call as a whole string. A chained call
(`git status; git branch --show-current`) does not match any
single-command rule regardless of ordering. In a headless session there
is no one to answer the resulting `ask` fallback, so the call fails
outright.

**Fix:** added an explicit instruction to `AGENTS.md` Rule 1: one command
per bash call, never chain with `;`, `&&`, or `|`, even when every
individual command is separately allowed.

### 5. Deterministic wrapper script for status+branch

To remove the *motivation* to chain in the first place (rather than
relying solely on a prose instruction, which is probabilistic — observed
to be followed inconsistently across runs), added
`scripts/git-context.ps1`, a fixed script returning `git status` and
`git branch --show-current` output in one call. Deliberately scoped to
only what the original failing chain needed — no base-branch diff logic,
which is a separate, already-solved concern (DEC-009).

Wired into global distribution: `setup.py`'s `build_links()` now includes
`scripts/` in both the OpenCode and Claude Code link tables (new `SCRIPTS`
constant, junction-linked same as `agents/`/`skills/`/etc.). Verified via
`python setup.py` — `~/.config/opencode/scripts` and `~/.claude/scripts`
both confirmed as working junctions.

Scoped to Windows/PowerShell only for now, matching this session's
observed environment (`opencode`'s bash tool runs via
`WindowsPowerShell\v1.0\powershell.EXE` on this machine). Cross-platform
(`.sh` equivalent) is an explicit, acknowledged gap, not solved here —
see Consequences.

### 6. Invocation-string variability defeated exact-match permission rule

Even with the script's path fixed, the model did not reliably reproduce
one exact invocation string across runs — observed three different
renderings of "the same" command: a plain relative path (failed — cwd is
the target project, not `ai-framework`), a `~`-prefixed path (failed — `~`
does not reliably expand when passed as a literal string argument to an
external process in Windows PowerShell, since it is a filesystem-provider
feature, not general string interpolation), and `$env:USERPROFILE`
(succeeded — genuine PowerShell string interpolation, correctly resolved
by the outer PowerShell process before invoking the inner `-File` call).

A PATH-based single-word shim (`git-context.cmd`) was considered as a
more robust fix (removes the path entirely, leaving minimal room for
stylistic variation) but explicitly rejected — declined to modify the
developer's global PATH, consistent with the framework's own existing
convention (see `install_rtk`'s detect-and-instruct-don't-auto-modify
pattern) of never silently editing machine-wide environment state.

**Fix:** standardized on the verified-working
`powershell -File "$env:USERPROFILE\.config\opencode\scripts\git-context.ps1"`
as the exact, canonical string, and updated `AGENTS.md` Rule 1 and both
agents' permission blocks to require and match it verbatim, including an
explicit note not to use `~`.

## Options considered (for #6 specifically)

1. **PATH shim, single bare word** — most robust against phrasing
   variation, but requires modifying the developer's global PATH.
   Rejected — inconsistent with framework convention.
2. **Multiple allow-listed string variants** — adds each observed
   rendering to the allowlist as it's found. Rejected as the primary
   fix — open-ended, does not converge, matches Core Principle 4's
   "guess" case rather than its "deterministic" case.
3. **Standardize on one verified-correct string, instruct verbatim**
   (chosen) — fully deterministic at the permission-matching layer; the
   only residual risk is whether the model reproduces the instructed
   string exactly, which is a smaller and better-understood risk than
   open-ended path-styling variation.

## Test evidence

Final confirmation run (`real branches` branch, no PATH
modification):
- `git-context` script invocation: `action.action=allow`, zero `ask`,
  zero `deny`, zero "does not exist" errors.
- `agent=orchestrator` confirmed active (not `build`).
- Check 1 (first-run analysis) fired correctly and stopped gracefully
  with a clear question, instead of a raw tool error (as it had
  previously, when `/review` was running under the unscoped `build`
  agent).
- Orchestrator additionally recognized the branch had no diff to review
  and asked clarifying questions rather than proceeding blindly or
  failing silently.
- **Not yet demonstrated:** a full pipeline run reaching an actual
  PASS/FAIL verdict end-to-end (`@code-reviewer` → `@qa` → `@gatekeeper`),
  since `real repos`'s `real branch` branch currently has no in-progress
  feature work to review. Dispatch and permission layers are confirmed
  clean; content-level pipeline execution is not yet exercised.

## Consequences

- `/task` should be re-verified with the same rigor as `/review` — it
  received the same `agent: orchestrator` fix, but has not been
  headlessly smoke-tested this session the way `/review` was.
- 13 of 15 agent files still carry the permission-ordering bug (#3) and
  are unverified. Should be prioritized before relying on any of them in
  a headless/unattended context.
- The chaining instruction (#4) is necessary-but-not-sufficient on its
  own — confirmed to be followed inconsistently across runs even after
  being added. Should not be treated as a complete fix in isolation;
  matters most in combination with #5's deterministic script.
- `scripts/` is currently Windows-only. Any Mac/Linux developer using
  this framework will hit the same "no reason to chain, but no
  deterministic script either" gap this session started from.
- This session's broader pattern — an initial hypothesis (chaining)
  turning out to be a correlated symptom of a deeper bug (ordering),
  which itself needed a third fix (invocation-string determinism) before
  being genuinely resolved — is worth carrying forward as a reason to
  keep verifying fixes with real runs rather than trusting a single clean
  result or a prior session's "confirmed correct" claim at face value.