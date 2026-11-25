# DEC-025 — Reviewed override of the changed-lines limit

**Status:** Accepted
**Date:** 2026-11-20

## Context

- The pre-push gate blocks a branch whose meaningful changed lines exceed `maxDiffLines` in `.ai-framework.json` (default 400; DEC-007, DEC-020, `execution/verification/checks/diff_size.py`). The key is already validated as a positive whole number.
- The only way past it today is `SKIP_DIFF_SIZE_CHECK=1 git push` (DEC-020 point 5): an environment variable the developer types, which turns the check off completely and leaves no record. The reason the gate hands to agents does not name it, and `tests/test_open_draft_pr.py` guards that.
- The quick lane has its own hard limits (3 files, 60 lines, DEC-018) and no override: over the limit, the lane ends.
- The developer's requirement (2026-11-20): a branch stays under the limit by default, the number is easy to change in the config file, and when the developer invokes an override command, in the style of `/quick`, the framework asks whether to continue as one PR or split into several.
- The gate already learns of developer decisions from commit trailers: `Lane: quick` (DEC-018) and `Dependency-Approved:` (step 3A.2).

## Options considered

- **A: keep only `SKIP_DIFF_SIZE_CHECK=1`.** Rejected: it is all-or-nothing and unlogged, and an orchestrator run cannot use it.
- **B: an override with an expiry, held in a state file, with commands to set and clear it** (the first sketch of S.6). Rejected: it needs a clock, a clear command, a place for the file (waiting for S.12) and a way for the hook to read it; state can go stale; and nothing shows in the PR.
- **C: a commit trailer `Diff-Size-Approved: <lines> <reason>` that sets a ceiling for that branch, read by the gate.** Chosen.
- **D: the agent raises `maxDiffLines` in `.ai-framework.json`.** Rejected: the change is permanent and applies to every later branch, and the agent rules forbid editing that file to get past a gate.

## Decision

1. **The standing limit is `maxDiffLines`,** unchanged: a positive whole number in `.ai-framework.json`, default 400. A project that finds 400 wrong changes the number there.
2. **The command is `/oversize <reason>`** (`commands/oversize.md`, a pointer to a section of `agents/orchestrator.md`, as `/quick` is). Only the developer declares it. No agent offers it, names it as a way past a blocked push, or infers it, and the reason is required. The developer types it after a push was blocked for size, not before, so the size it approves is the final size.
3. **What the orchestrator does.** It measures the branch with `scripts/diff-size-check.py` and reads the `STATUS:` line. If the branch is not over the limit it says so and stops. If it is over, it reports the lines and the limit and asks the developer to choose: continue as one PR, or split. On split it hands the branch to the architect step for an atomic-changes breakdown. On one PR it makes an empty commit whose message carries `Diff-Size-Approved: <lines> <reason>` (the measured number, not rounded), runs the push script again, and repeats the number and the reason in the task summary and the draft PR body.
4. **What the gate does.** `checks/diff_size.py` reads the commit messages from the merge-base of the base and the pushed commit up to the pushed commit, the same range it measures, so an approval made before an earlier push still counts for a later push of that branch.
   - A trailer line is a line that, after trimming, starts with `Diff-Size-Approved:`. It must read `Diff-Size-Approved: <N> <reason>` with N a positive whole number of at most 9 digits (a detail fixed in S.6b) and a non-empty reason. Any other line that starts that way blocks the push and names the commit (DEC-015 point 3: fail closed).
   - The limit for the branch is the larger of `maxDiffLines` and the largest N on the branch. A branch over that limit is blocked, and the message names the approved number when there is one.
   - A trailer on a branch that is not over the limit changes nothing.
5. **`SKIP_DIFF_SIZE_CHECK=1` is unchanged:** the developer's unlogged way to turn the check off. The trailer does not skip the check; it raises the number the check compares against, and the branch is still measured.
6. **The quick lane is unchanged.** Its limits are checked by `quick_lane.py` and the trailer does not touch them; a `/quick` change over the lane limits still ends the lane.

Touches (planned, two PRs): `execution/verification/checks/diff_size.py`, `execution/verification/run.py` and `skills/atomic-changes/SKILL.md` (the gate, S.6b); `commands/oversize.md` (new), `scripts/diff-size-check.py` (new), `agents/orchestrator.md` and the README command list (the command, S.6c).

Settled in S.6c (2026-11-20): `scripts/diff-size-check.py` imports the gate's own functions (the framework folder is found beside the script, else through the global git setting `aiFramework.root`), so there is no second copy of the count to keep in step. Split changes nothing in git: the architect step proposes the breakdown table for the work already on the branch and the developer splits the commits, because an agent may not rebase or reset. The empty approval commit passes `commit-msg` because its subject follows the conventional format (the hook accepts a message when any line matches), and `pre-commit` blocks only `main`, `master` and `develop`.

## Reasoning

1. **Agent or deterministic?** The declaration is the developer's decision. Measuring a branch and comparing it with a number is deterministic, so a script and the gate do it. The agent reads `STATUS:` and writes the trailer for the number the developer approved.
2. **Trade-offs.** The trailer has the trust level of `Dependency-Approved:`: a model could write it without being asked. The protections are that the command is the only entry and the orchestrator is told never to add or name it otherwise; that the ceiling is the exact number the developer saw, so a later commit that grows the branch is blocked again until the developer declares again; and that the reason stays in history. The approval commit adds one empty commit to the branch.
3. **Cheaper way?** Raising `maxDiffLines` in the config is already possible and is the right tool when 400 is wrong for a project. It is permanent, so it is the wrong tool for one exception.
4. **What a developer can now see or do.** Set `maxDiffLines`. After a push is blocked as too big, type `/oversize <reason>`, choose one PR or a split, and get the push. `git log --grep "Diff-Size-Approved"` lists every approved exception with its reason.

## Consequences

- The S.6 plan row asked for set, expiry, clear and a log. This design has no state to expire or clear: the approval is per branch and lives in git history. To withdraw it before pushing, the developer drops the commit locally. S.6 no longer waits for S.12 or S.7.
- The gate reads `.ai-framework.json` from the repository path it is given (`_read_config` in `run.py`), so editing the file still changes the limit. Only the text of the orchestrator and `pr-provider` forbids an agent from doing so (read 2026-11-20). The trailer adds no new way around the limit and is easier to audit than that edit. Not changed here.
- The manual size check (`git diff -w --ignore-blank-lines origin/main HEAD | grep -E '^[+-][^+-]' | wc -l`) and the gate agree within a few lines: on PRs #122 and #123 they gave 236 and 231 by hand and 231 and 232 by the gate. Both count deleted lines. The gate skips import-only lines and counts lines that start with `+` or `-`, which DEC-020 already records. A change near the limit is judged by the gate's number.
- A commit message that starts a line with `Diff-Size-Approved:` in any other form blocks the push, even on a branch under the limit (point 4); reword such a message so that no line starts with those words.
- Evidence: `tests/test_diff_size_approval.py` (the parser, the ceiling, real git repositories and the `run.py` wiring; S.6b). The command PR adds wording guards in the style of `tests/test_quick_lane_wording.py`.
