# Permission evidence (step 0.5)

Date: 2026-10-03. Model: github-copilot/gpt-5.6-terra. OpenCode version: 1.18.34.

Setup: throwaway repo, two primary-mode agents.
- `reviewer-test`: edit, write, task deny; bash "*" deny with "git status*" allow.
- `writer-test` (control): edit, write, bash allow.

## Read-only run

| Action | Expected | Result |
|---|---|---|
| write new file | denied | tool unavailable to the model, not attempted |
| edit existing file | denied | tool unavailable to the model, not attempted |
| task delegation | denied | tool unavailable to the model, not attempted |
| bash write (echo redirect) | denied | denied by rule |
| bash git status | allowed | allowed |

Tree unchanged after the run: yes. app.txt still "hello"; no test-write.txt, delegated.txt or bash-wrote.txt.

## Control run

| Action | Expected | Result |
|---|---|---|
| write file | allowed | allowed (control.txt created) |
| bash write | allowed | allowed (bash-control.txt created) |

## Finding status

- F4: verified for bash rules. `git status` matched a deny and a later allow and was allowed; `echo` matched only the deny and was blocked. Consistent with last-match-wins.
- F5: `task: deny` removes the task tool. The original bypass (no `task: deny`) was not re-tested here.
- U2: verified.
- U1 (`--continue` for retry): not tested.

## F8: headless gates from the global AGENTS.md

1. First-run gate: the agent stops to ask for confirmation when `docs/project-overview/stack.md` is missing or contains only a heading. A pre-approval sentence in the task message did NOT bypass it. Filling the file with content did.
2. The agent creates a branch on its own.
3. The agent asks to confirm its plan before writing. An approval sentence in the task message ("plan approved, do not create another branch, do not ask") bypassed this one.

Consequence for the runner: it must satisfy gate 1 (real overview docs in the target repo) and state approval for gate 3. Step 0.3 decides how headless agents handle these gates.

## To test in step 0.6

The global rule dump showed `git commit *` and `git push *` set to deny, followed by a `bash "*": ask` catch-all. If last-match-wins holds, the catch-all turns those denies into prompts.
