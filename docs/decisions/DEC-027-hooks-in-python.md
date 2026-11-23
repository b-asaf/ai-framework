# DEC-027 — The git hooks run as Python, and build-verify moves out of hooks/

**Status:** Accepted
**Date:** 2026-11-20

## Context

- Decision #10 (2026-11-14, step S.7): all hooks run as Python, the hook files are only launchers, and hooks that are not needed or duplicate another check are deleted.
- Before this change `hooks/pre-push` was a launcher plus about 50 lines of shell that read `.ai-framework.json` with `grep` and `sed` and ran `hooks/build-verify.sh`. `hooks/pre-commit` and `hooks/commit-msg` were 15-line shell scripts without tests: `pre-commit` hard-coded `main master develop` (DEC-009 moved push protection to `origin/HEAD` and `protectedBranches`), and `commit-msg` accepted a message when any line matched the format.
- R1 (verified 2026-11-20): six implementation agents allow and call the relative path `hooks/build-verify.sh`. A project has no such file (the call exits 127), so their self-check loop failed in every project. The script existed only in the linked tool folders and in `.git/hooks`.
- `hooks/session-end.js` was a link to a file that nothing used; only docs named it.

## Options considered

- **A: keep the shell hooks and fix only the agents' path.** Fixes R1 and keeps two untested hooks and a JSON reader made of `grep`.
- **B: one Python script per hook.** Three launchers to keep in step and three copies of the interpreter search.
- **C: one launcher under three names, one Python edge script, and `build-verify` as a Python script in `scripts/`.** Chosen.

## Decision

1. `hooks/pre-commit`, `hooks/commit-msg` and `hooks/pre-push` are byte-identical. The launcher finds `aiFramework.root` and a working Python 3 (`AI_FRAMEWORK_PYTHON`, `python`, `py -3`, `python3`), drops the local git variables and runs `execution/verification/hook.py <hook name> <hook arguments>`. A missing root, a missing edge script or a missing Python blocks with a fix message, for all three hooks, as `pre-push` already did. A test fails when the three files differ.
2. `execution/verification/hook.py` holds the checks. `pre-push` runs the existing push gate and then the build-verify stage.
3. `commit-msg` judges the first line that is not blank and not a `#` comment, with the unchanged pattern. A message whose first line is wrong is now rejected even when a later line looks conventional.
4. `pre-commit` blocks a commit on a branch in the protected set of the push gate: the branch `origin/HEAD` points to, plus `protectedBranches`. Where neither exists, or the config cannot be read, the old list `main master develop` applies, so a repository without a remote is protected as before. Where `origin/HEAD` exists and nothing else is configured, `develop` and `master` are no longer blocked at commit time; a project lists them in `protectedBranches`.
5. `build-verify` becomes `execution/verification/build_verify.py` (the code) and `scripts/build-verify.py` (what agents run, in the form of every other helper: `python "$HOME/.config/opencode/scripts/build-verify.py"`, allowed by `python *scripts*build-verify.py*`). It reads the lint, format and test commands of `.ai-framework.json` as JSON, so the agent loop and the push gate cannot drift apart; with `--lint`, `--format` or `--test` it runs only the stages named. Stages run through `sh -c` in the repository root, as the old `eval` did. Exit codes: 1 lint, 2 format, 3 test failed, 4 it cannot run (no `.ai-framework.json` or no command, a value that is not text, no shell, a bad flag); the shell script also used 2 for a bad flag. Logs go to the git folder, which also works in a linked worktree.
6. The six implementation agents and the `build-verify` skill call the script by that path; `hooks/build-verify.sh` and `hooks/session-end.js` are deleted.
7. `setup.py` copies and checks three hooks, and removes a retired `build-verify.sh` from the git template and from a repository on `--install-hooks`.
8. The escapes are unchanged: `--no-verify`, `SKIP_VERIFICATION`, `SKIP_DIFF_SIZE_CHECK`, `SKIP_BUILD_VERIFY` and `AI_FRAMEWORK_PYTHON`.

## Reasoning

1. **Agent or deterministic?** Deterministic throughout: a branch name, a message format, exit codes. The agent only reads the exit code.
2. **Trade-offs.** Commits now need Python and a configured framework folder, like pushes: after the framework folder moves, commits block until `python setup.py` runs. The first-line rule can reject a message that the any-line rule accepted. A project whose `.ai-framework.json` holds a lint, format or test value that is not text now blocks at push; the `grep` reader ignored it.
3. **Cheaper way?** Fixing only the agents' path (A) is cheaper and was rejected because it keeps two untested hooks and the `grep` JSON reader.
4. **What a developer can now see or do.** The agents' self-check loop runs in every project; one launcher and one edge script replace three shell scripts; each hook has a test on real git.

## Consequences

- Repositories that already have the shell hooks keep working: the old `pre-push` calls the `build-verify.sh` beside it in `.git/hooks`. They switch when `python setup.py --install-hooks <repo>` runs, which also removes that file; `python setup.py --verify` reports hooks that differ.
- A hook now blocks when it cannot start: `aiFramework.root` unset, the edge script missing from an older framework folder, or no Python 3.
- Only the six implementation agents got the new allow line; the orchestrator and the other agents are unchanged.
- Evidence: `tests/test_hook.py` (commit-msg, pre-commit, the edge script and the launcher on real git), `tests/test_build_verify.py` and `tests/test_pre_push_hook.py`.
