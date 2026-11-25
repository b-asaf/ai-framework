# DEC-029 — Branch protection belongs to the git host

**Status:** Accepted
**Date:** 2026-11-24

Supersedes the protected-branch detection of DEC-009, the `pre-commit` protection of DEC-027 and the last line of the Consequences of DEC-020.

## Context

- The pre-push `branch_protection` check blocked a push to the branch `origin/HEAD` points to or to a `protectedBranches` entry, and blocked every push when neither resolved. The S.7 `pre-commit` hook used the same set.
- A local hook is skipped by `--no-verify`, and it never runs in a repository with its own `core.hooksPath` (bta-frontend). The branch policy of GitHub, GitLab and Azure DevOps cannot be skipped from a laptop, and both real projects have one.
- `dependency_change` and `quick_lane` took "the first protected branch" as the base of a new branch, so a protection list also decided a diff range (DEC-020 noted the exposure). bta-backend has `origin/HEAD` = `temp-dev` and works from `dev`.
- The developer's guidelines (2026-11-24): protected branches are the responsibility of the git host and not of the framework; each change is made on a new branch unless the developer declares the quick lane, which works on the current branch.

## Options considered

- **A: keep the local protection.** Two sources of truth, and one of them can be bypassed.
- **B: keep an `origin/HEAD`-only check and drop the key.** Still a bypassable copy of the host's rule.
- **C: remove the local protection and give `dependency_change` and `quick_lane` the base of `diff_size`.** Chosen.

## Decision

1. Protected branches are enforced by the git host, not by the framework. The `branch_protection` check is removed from the push gate, and the `pre-commit` hook checks nothing. The hook stays only so that launchers already installed in repositories keep working; dropping it from the install list is a later cleanup.
2. The base of a new-branch range is the same for `diff_size`, `dependency_change` and `quick_lane`: `diffBaseBranch` if set, else `origin/HEAD`, else the push is blocked with a fix message (DEC-015 point 3 still holds). `run.py` resolves it once with `diff_size.read_base`.
3. `protectedBranches` is read by nothing and first-run does not ask for it. A leftover key in `.ai-framework.json` is ignored. A test fails if live code or text names it.
4. Every task gets a new branch. In the regular lane, on a branch that is not the base, the orchestrator asks only where the new branch starts (from the current branch or from the base). The quick lane (`/quick`, declared by the developer only) works on the current branch; on the base branch it first creates a `fix/` or `chore/` branch. The quick lane's own limits and gates do not change.
5. The lane has one name in prose, the quick lane. The command is `/quick`, the key is `quickLane`, the commit trailer is `Lane: quick` and the check is `quick_lane`. "Fast lane" in DEC-017, DEC-018 and DEC-025 is the old name of the same thing.
6. `SKIP_VERIFICATION=1` skips `dependency_change` and `quick_lane`. Nothing is left that "stays on".

## Reasoning

1. **Agent or deterministic?** The host's rule is the authority. The agent text only decides which branch the work happens on.
2. **Trade-off.** A repository with no host policy has no protection against a push to its default branch. The developer accepted this: the host is the authority.
3. **Cheaper way?** Keeping the check costs a second rule that can disagree with the host's, and a base that depended on it.

## Consequences

- A repository whose `origin/HEAD` is not the branch its work starts from sets `diffBaseBranch` (for example `origin/dev`), which also fixes the diff-size base.
- A new-branch range is measured against `diffBaseBranch` or the remote-tracking `origin/<default>`, no longer against a local branch name, so a stale local `main` cannot skew it.
- A quick fix on a branch that already has commits joins that branch's PR; the orchestrator says "Working on `<current>`" so it is visible.
- Evidence: `tests/test_quick_lane_wording.py`, `tests/test_pre_push_hook.py` and `tests/test_verification_run.py` (a push to `main` is not blocked by the framework; the base comes from `diffBaseBranch`, then `origin/HEAD`).
