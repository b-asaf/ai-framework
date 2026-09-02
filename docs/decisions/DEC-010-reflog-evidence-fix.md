# Decision: Fix reflog-evidence resolution in pre-push diff-base detection

**Date:** 2026-08-30
**Status:** accepted

## Context
DEC-009 set the diff-base resolution order for the pre-push diff-size
backstop: explicit `diffBaseBranch` config, then unambiguous git reflog
evidence, then an honest skip — never a guess. The reflog-evidence path was
smoke tested on `real project` as part of five pre-push test scenarios
(protected-branch blocking, `diffBaseBranch` explicit path, reflog-evidence
path, honest-skip case, meaningful-line filtering). Scenarios 1, 2, 4, and 5
passed unmodified; the reflog-evidence path failed twice, in two different
ways, before passing.

**Bug 1.** The original implementation read the target branch's own reflog
(`git reflog show <branch>`) for a `branch: Created from <X>` entry. That
entry only names a real ref if `checkout -b <name> <start-point>` was given
an explicit start-point. Plain `git checkout -b <name>` — the common case —
records the literal string `Created from HEAD`. By the time the hook runs,
`HEAD` resolves to the new branch's own tip, so `git rev-parse --verify
HEAD` succeeds, `BASE_BRANCH` gets set to `HEAD`, and `merge-base HEAD HEAD`
diffs the branch against itself: always zero changed lines, no error, no
skip message. Looks identical to "compliant" whether or not the branch
actually exceeds the limit. Confirmed via:
```
3c6cc181 (origin/dev, dev) test/reflog-base@{1}: branch: Created from HEAD
```

**Bug 2.** The fix for Bug 1 (read `HEAD`'s own reflog for `checkout:
moving from <X> to <branch>`, which reliably names the real source
regardless of an explicit start-point) used `/` as the `sed` substitution
delimiter. Branch names routinely contain `/` (`test/reflog-base2`,
`feature/x`) which broke the substitution outright (`sed: unknown option to
's'`). Same symptom as Bug 1 from the user's side — looked like a clean
skip — different cause: a shell/tooling bug, not a git-semantics gap.

## Options considered
- **A — special-case the literal `HEAD` value in the branch's own reflog**
  parse, and fall back to something else when detected. Minimal diff, but
  leaves the underlying source (a reflog that only records real ref names
  conditionally) fragile, and doesn't touch Bug 2 at all.
- **B — require `diffBaseBranch` in config for every project**, drop the
  reflog path entirely. Deterministic and simple, but pushes a config
  burden onto every new project before diff-size enforcement works at all,
  against Principle 1 (simplicity/minimal setup).
- **C (chosen) — read `HEAD`'s own reflog instead of the branch's**,
  filtering `checkout: moving from <X> to <branch>` and taking the oldest
  match as the creation point; separately, switch the `sed` delimiter from
  `/` to `#`, since `#` cannot appear in a git ref name.

## Decision
Adopt Option C. Both fixes preserve DEC-009's core rule — unambiguous
evidence or honest skip, never a guess. If `HEAD`'s reflog has no matching
entry (reflog expired, shallow clone, reflogs disabled), the hook falls
through to the same skip message as before, confirmed in scenario 4.
This touches only `hooks/pre-push` (`ai-framework`) and its installed copy
in each target project's `.git/hooks/pre-push`.

## Reasoning
1. Fully deterministic, same as the rest of the diff-base logic it
   corrects — no agent/LLM judgment involved in either bug or fix.
2. Trade-off is a slightly more involved two-step grep+sed parse in
   exchange for correctness on the common case (`checkout -b` with no
   explicit start-point) and on slash-named branches — no new dependencies,
   no meaningful cost increase.
3. A cheaper fix would be Option B (drop reflog, require config
   everywhere), but that trades a one-time hook-logic cost for a recurring
   per-project config burden on every developer — worse overall given how
   many projects this framework targets.
4. A developer using `ai-framework` can now get correct diff-size
   enforcement on a normally-created feature branch (`git checkout -b
   <name>`, no special flags) with zero config, including branches named
   with the common `type/description` convention — neither worked
   reliably before this fix.

## Consequences
- `hooks/pre-push` (source) and both installed copies
  (`[project-name]/.git/hooks/pre-push`, template via `git-template/hooks/`)
  needed updating; done and reverified against `real project`.
- **Known remaining limitation, not fixed here:** the `grep -E` filter
  builds its pattern using the branch name directly inside an extended
  regex. `/` is confirmed safe (not special in ERE), but a branch name
  containing regex metacharacters (`.`, `*`, `+`, `[`, etc.) could still
  cause a mismatch. Left open — real escaping complexity for a much rarer
  case than the two fixed here. Flag for a future DEC if it surfaces.
- Confirms the established pattern (DEC-008, DEC-009): real smoke testing
  keeps finding design gaps reasoning alone didn't surface. Not a process
  failure — expected to keep happening.
- `CHANGELOG.md` and version number need updating alongside this entry
  (separate from this file; version-bump mechanics still being confirmed
  against `setup.py`/`CHANGELOG.md`/`README.md`).

## Test evidence
Reproduced and fixed live against `real project` using disposable branches
(`test/reflog-base`, `test/reflog-base2`, `test/reflog-base3`), each pushed
then deleted from origin. Final passing run:
```
ERROR: This branch changes 7 meaningful lines (vs dev,
  base via reflog (HEAD 'moving from' entry)) - exceeds the atomic-changes limit of
  5 lines (skills/atomic-changes/SKILL.md).
```
Correctly resolved `dev` as base, correct meaningful-line count, blocked
before any network activity reached the remote.
