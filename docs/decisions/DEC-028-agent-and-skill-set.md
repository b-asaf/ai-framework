# DEC-028 — The agent set, the skill set and the name of the stack file

**Status:** Accepted
**Date:** 2026-11-23

## Context

- Plan steps S.4 (the 15 agents), S.5 (the 44 skills) and S.12f (the spelling of the stack file), decided together because the same files name all three.
- Evidence read on 2026-11-23:
  - The six implementation agents (`api`, `backend`, `db`, `frontend`, `frontend-error-fixer`, `ui`) are 80 to 106 lines, use the same model (`claude-sonnet-5`), and have identical `ask` rules (25 lines, same hash). They differ in the skills they load: against `backend`, `frontend` differs by 39 diff lines, `ui` by 72, `api` and `db` by 77, `frontend-error-fixer` by 106. They carry 12 of the 16 independence edges in `execution/policy.json`, each against `code-reviewer` and `qa`, which are GPT.
  - `surgical-changes` is loaded only by `frontend-error-fixer`; AGENTS.md rule 10 is the only source of that rule for the other implementers. `code-standards` (loaded by 10 agents) repeats rule 6; the eight `clean-code-*` skills (418 lines) are loaded only by `code-reviewer` and through the `code-standards` table.
  - `mutation-testing` (134 lines) is named by no agent or skill. Neither real project (`bta-backend`, `bta-frontend`) configures Stryker or PIT. DEC-006 and DEC-008 describe the same correction in near-identical words.
  - The first-run output of both real projects has a flat `docs/project-overview/stack.md` and uses `sub/` only for the other files; 15 agent files, the skill table and the README named `project-overview/sub/stack.md`.

## Options considered

- **Agents:** keep the six with a drift test (chosen); generate them from one template (a generator, a drift check and a change to plan 5.8, where agents are hand-written); merge them into fewer agents (loses deterministic per-role skill loading, AGENTS.md rule 8, and cuts the independence edges from 12 to a few).
- **Skills:** merge the eight `clean-code-*` skills into `code-standards` (rejected: a conditional load becomes an always-load for 10 agents, a cost of about 5,000 tokens a session, against rule 14); turn rules 6, 7 and 10 into pointers (rejected: see the decision); delete `mutation-testing` (chosen) or wire it into `code-reviewer` as a stage (rejected: an LLM-run stage for a tool no project uses, against DEC-015).

## Decision

1. **The six implementation agents stay.** `tests/test_agent_set.py` fails when their `ask` rules differ or one of them stops loading `build-verify`.
2. **`plan-reviewer` stays** (DEC-017's second approval checkpoint). Step 3B.2 is done after the 4.5 soak, when real designs exist to test it on. Step 3C (the throwaway pipeline experiment) is deferred: the soak does not need it.
3. **`mutation-testing` is deleted** (43 skills). DEC-006 and DEC-008 stay as history. If a project wants mutation testing, it comes back as a code check, not as an agent stage.
4. **The `clean-code-*` skills stay separate, and rules 6, 7 and 10 stay in AGENTS.md.** A pointer to `surgical-changes` would remove rule 10 for five of the six implementers, and rules 6 and 7 are two lines and one line.
5. **A skill that nothing names is a test failure** (`tests/test_agent_set.py`): the name must appear in an agent, command, instruction file, another skill, AGENTS.md or the README.
6. **The stack file is `project-overview/stack.md`** (S.12f). The agent files, the README and the skill table say so, and the skill template's `stack.md` moved up out of `sub/`, so that a first-run that mirrors the template writes what the two projects already have: `stack.md` in the folder and the other files in `sub/`. The runner fixture without `sub/stack.md` is gone.

## Reasoning

1. **Agent or deterministic?** Which skills an agent loads is a deterministic list in its file (rule 8), and a test checks what is checkable in code (DEC-015).
2. **Trade-offs.** Keeping six similar files means a shared change is made six times, as in DEC-012 and S.7; the drift test turns a missed file into a failing test. Keeping the eight skills costs files and gains selective loading.
3. **Cheaper way?** A generator would remove the repetition for the price of a second source of truth for agent files.
4. **What a developer can now see or do.** One name for the stack file, 43 skills that are all in use, and a test that names the file that fell out of step.

## Consequences

- **Findings, not changed here:** `backend` is the only implementer that does not load `agent-guidelines` (the other five do). **Resolved in S.13 (DEC-030):** `backend` now loads it. `bta-frontend` has `core.hooksPath` set to `.husky/_`, so git ignores `.git/hooks` there and the push gate never runs; `--install-hooks` refuses such a repository. `bta-backend` has no `test` command in `.ai-framework.json`, so the push gate blocks every push until it has one.
- Existing projects keep a `docs/project-overview/` that the agents no longer read: delete the generated files and let the first-run analysis write them again under `.ai-framework/`.
- The deleted skill counts toward the major version bump of step 4.6.
- Evidence: `tests/test_agent_set.py`.
