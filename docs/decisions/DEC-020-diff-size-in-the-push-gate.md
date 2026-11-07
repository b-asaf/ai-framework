# DEC-020 — Diff-size check in the push gate

**Status:** Accepted
**Date:** 2026-11-06

## Context

- DEC-007 added a 400-line backstop to the shell `pre-push` hook. DEC-009 and DEC-010 gave it a base from `diffBaseBranch` or from reflog evidence, and said to skip the check when neither exists.
- F68: in a worktree the reflog has no checkout entry for the branch, so the check skipped itself in every push so far. PR #79 changed about 485 meaningful lines and nothing stopped it.
- DEC-015 point 3 says a check that cannot decide blocks with a readable reason and never skips.

## Options considered

- **A: `diffBaseBranch` if set, else origin's default branch (`origin/HEAD`), else block.** Chosen.
- **B: require `diffBaseBranch` in every repository.** Strictest, but every repository needs the key before its first push.
- **C: keep the reflog guess and the skip, and set `diffBaseBranch` here.** Fixes one repository and leaves DEC-015 point 3 broken.

## Decision

The check is `execution/verification/checks/diff_size.py`, run by the Python gate (`run.py`).

1. The base is `diffBaseBranch` when set (it must resolve, otherwise the push is blocked), else `origin/HEAD`, else the push is blocked with a fix message. Repositories that branch from something other than the default branch set `diffBaseBranch`.
2. The measured range is `merge-base(base, pushed commit)` to the pushed commit, the whole branch, so a second push of a big branch is still caught. Deletes count 0.
3. Counted: added and removed lines from `git diff -U0 -w --ignore-blank-lines -M`, without blank lines and import-only lines (as DEC-009). Pure renames are not counted.
4. The limit is `maxDiffLines` in `.ai-framework.json` (a positive whole number, default 400). A bad value blocks.
5. `SKIP_DIFF_SIZE_CHECK=1` stays the only way to skip this check, and it never skips branch protection.
6. The shell section of `hooks/pre-push` is removed in the next PR.

This supersedes the skip rule and the reflog strategy of DEC-009 and DEC-010 for this check. The rule that the hook never picks the first protected branch still holds: `origin/HEAD` is one fact, not a choice among branches.

## Reasoning

1. **Agent or deterministic?** Deterministic: a count of lines against a limit.
2. **Trade-off.** A branch cut from `dev` and measured against `main` is over-counted, so those repositories must set `diffBaseBranch`. A repository without `origin/HEAD` and without the key is blocked until it has one. That is the cost of not skipping.
3. **Cheaper way?** Setting `diffBaseBranch` here fixes one repository only.

## Consequences

- Lines that start with `+` or `-` (a markdown bullet, for example) are counted now. The shell filter ignored them, so some branches measure a little larger than before.
- `dependency_change` and `quick_lane` use the first protected branch as the base of a new branch, which has the same exposure. Not changed here.
- `skills/atomic-changes/SKILL.md` and the DEC-009 note are updated in the PR that removes the shell section.
