# DEC-024 — Folder layout (plan step S.3)

**Status:** Accepted for points 1 to 3 (developer, 2026-11-18). Points 4 to 7 are proposals and stand unless the developer objects in review.
**Date:** 2026-11-18

## Context

- S.3 asked which top-level folders stay, merge or go. The evidence is in `docs/framework-audit-2026-11.md` and in its section "Answers to the open questions".
- Folders today (tracked files, 2026-11-18): `agents/` 15, `commands/` 5, `docs/` 33, `execution/` 32, `hooks/` 5, `instructions/` 7, `scripts/` 4, `skills/` 59, `tests/` 104, `tools/` 12.
- `scripts/` holds helpers that agents, hooks and gates call by path (`git-context.py`, `static-analysis.py`, `quick-lane-check.py`, `open-draft-pr.py`); `setup.py` links it into the OpenCode and Claude config folders. `tools/` holds the validator, the routing generator and `tools/lib`, which the validator and the runner import; `setup.py` does not link it.
- The README block "Repo structure" omits `execution/`, `tools/` and `tests/` and describes `scripts/` as holding one graphify script that no longer exists.

## Options considered

- **A: merge `scripts/` and `tools/`.** One folder, but maintainer code would sit in the folder that `setup.py` links into every tool config.
- **B: keep both and say in the README which is which.** Chosen.
- **C: split `tools/lib` out into `execution/`.** Cleaner imports, but it edits about ten files and their `sys.path` lines for no behavior change.

## Decision

1. **Folders that remain:** `agents/`, `commands/`, `docs/`, `execution/`, `instructions/`, `scripts/`, `skills/`, `tests/`, `tools/`, and `hooks/` until S.7 decides whether it stays a folder. Nothing is merged into another folder.
2. **`scripts/` and `tools/` stay apart.** `scripts/` is for helpers that run during a task, called by agents, hooks and gates, and linked into the tool config folders. `tools/` is for the maintainer: the validator, the routing generator and their shared code. It is not linked.
3. **The README explains every top-level folder.** The "Repo structure" block gets one purpose line per folder and states the `scripts/` and `tools/` split in words. A test in `tests/` fails when a tracked top-level folder is missing from that block (plan step S.11, brought forward to the PR after this one).
4. **Proposed:** `tools/lib` stays. The README says the runner imports it. Revisit if a second consumer outside `tools/` and `execution/` appears.
5. **Proposed:** delete `tools/validate_agents.py` (a 14-line wrapper used only by `tests/test_entry_points.py`) and adapt that test; move `tools/test_gap1_delegation.py` (a log-analysis script for DEC-013, probably not run by `unittest`) to `tests/bench/` without the `test_` prefix, or remove it.
6. **Proposed:** keep all seven files of `instructions/` for now. `wire_vscode` in `setup.py` (lines 349 to 374, read 2026-11-18) writes `AGENTS.md`, `COPILOT.md` and `VSCODE.md` into one VS Code user setting, so merging the two Copilot files is possible for VS Code; `VSCODE.md` is used only there, and `COPILOT.md` is also linked for other Copilot clients (setup.py lines 112 to 118, not read). Neither header matches the code: both say the file is wired to `.github/copilot-instructions.md`, and `wire_vscode` writes user settings and no project file. The merge is decided in S.10b after both files are read, and the headers are fixed in the same PR.
7. **Proposed:** `hooks/` follows decision #10 (S.7): the hooks become launchers over Python, `hooks/session-end.js` is deleted, and `build-verify.sh` moves out of `hooks/`, because it is not a git hook.

## Reasoning

1. **Agent or deterministic?** Neither: this is a layout decision. The README test makes the rule deterministic.
2. **Trade-off.** Two small helper folders instead of one, in exchange for keeping maintainer code out of the linked folder.
3. **Cheaper way?** Option B costs a README block and a test.
4. **What the developer sees.** A README that says what each folder is for, and a check that keeps it that way.

## Consequences

- The moves in points 5 and 7 are separate PRs (plan steps S.10a, S.10b and S.7), each with its own evidence.
- Findings that belong to S.5 and S.7 and not to this layout are listed in the audit file: `mutation-testing` is named by no agent or skill, six agents call `hooks/build-verify.sh` by a relative path that a project does not contain, and AGENTS.md rules 6, 7 and 10 repeat skills.
- `wire_vscode` rewrites the developer's VS Code `settings.json` without a backup (audit findings 24 and 25); the fix is plan step 5.3c, after the characterization tests of 5.3.
