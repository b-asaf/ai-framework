# DEC-021 — Remove ccusage from the framework

**Status:** Accepted
**Date:** 2026-11-17

## Context

- Plan decision #12 (S.8): the developer asked whether the framework needs ccusage and decided on 2026-11-17 that it is removed completely and does not come back.
- What exists (tracked files, `git grep`, 2026-11-17): `install_ccusage` in `setup.py` and its call in `main` (step 6, "Token monitoring"), the folder `monitoring/` (one file, `monitoring/README.md`, 47 lines), and one row of `docs/session-summary.md`. No agent, skill, command or code calls it. `npx ccusage@latest daily` runs without an install.
- The per-agent usage table (plan step 5.5, decision #6) takes its data from the RunRecords, so it does not need ccusage.

## Options considered

- **A: keep it.** It is an installer for a tool nothing in the framework uses.
- **B: delete it.** Chosen.

## Decision

Delete `install_ccusage` and its call in `setup.py` (and renumber the step comments that follow), the folder `monitoring/`, and the ccusage row of `docs/session-summary.md`. One PR (plan step S.8a). Older mentions in `CHANGELOG.md` and in earlier decisions stay as history.

## Reasoning

1. **Agent or deterministic?** Neither: this removes an unused installer.
2. **Trade-off.** Cross-tool token dashboards are no longer set up by `setup.py`. A developer can still run ccusage on their own.
3. **Cheaper way?** Keeping the code costs lines in a file that has no tests (plan step 5.3).
4. **What the developer sees.** A shorter `setup.py` and no `monitoring/` folder.

## Consequences

- A global `npm install -g ccusage` that an earlier `python setup.py` made stays on the machine unless the developer removes it.
- The PR keeps the output of `python setup.py --verify` unchanged.
