# Git autonomy evidence (step 1.9, part A)

Date: 2026-10-11. Model: github-copilot/gpt-5.6-terra. OpenCode version: 1.18.34.

Setup: a throwaway repo with one agent that has no bash rules of its own, so it inherits the global rules. The global config was an isolated copy of the new `opencode.json` (`XDG_CONFIG_HOME`) with one extra probe rule (`git tag xdg-probe*`: allow) and no `AGENTS.md`.

| # | Command | Expected | Result |
|---|---|---|---|
| 1 | `git tag xdg-probe-one` | allowed (proves the isolated config was in effect) | allowed; the tag exists |
| 2 | `git checkout -b chore/autonomy-check` | allowed | allowed; branch created |
| 3 | `git commit --allow-empty -m chore-test` | denied | denied by rule `git commit *`; the log still shows only the initial commit |
| 4 | `git push origin main` | denied | denied by rule `git push*` |
| 5 | `git branch -D chore/autonomy-check` | denied | denied by rule `git branch -D *` |
| 6 | `gh pr ready` | denied | denied by rule `gh pr ready*` |
| 7 | `npm install lodash` | not run silently | `permission requested ... auto-rejecting`; nothing installed |

## Findings

- F19: `XDG_CONFIG_HOME` pointing at a folder with `opencode/opencode.json` isolates the global config. The probe tag shows the override is active.
- The rule list the agent received has the default `* allow *` first, then the bash catch-all, then the specific rules in file order. This is consistent with last-match-wins (F4, F9).
- The isolated config had no `AGENTS.md`, so the first-run, branch and plan-confirmation gates did not apply. This run shows permissions only; the gates are instructions (part B).

## Not tested

- The orchestrator's own block, which overrides the global rules. Checked in part B.
- Interactive prompts. Only the headless auto-reject was observed.

## Part B: orchestrator block (step 1.9, DEC-017)

Date: 2026-10-12. Model: github-copilot/claude-sonnet-5.

Setup: two test agents built from the real orchestrator frontmatter, run in a throwaway repo with the isolated global config. `orch-test` is the current block. `orch-old-test` lacks the nine new denies (`git branch -d/-D/--delete`, `git commit*--no-verify*`, `gh pr ready/merge/create`, `glab mr merge/create`).

| Command | New | Old |
|---|---|---|
| `git checkout -b chore/orch-check` | ran | git refused (the branch existed from the first run); no permission rule involved |
| `git branch -D chore/orch-check` | denied by rule | allowed; git refused because the branch was checked out |
| `git commit --no-verify -m chore-x` | denied by rule | allowed; git said nothing to commit |
| `gh pr ready` | denied by rule | `permission requested ... auto-rejecting` (a prompt, not a deny) |
| `git push origin main` | denied by rule | not reached in the output |

Finding F20: in the merged rule list the agent's own `"*": ask` comes after the global denies, so it overrides them. The global `gh pr ready*` deny did not protect the old orchestrator, which was only prompted. Agents that can commit repeat the denies in their own block, and the validator enforces it.
