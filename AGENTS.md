# AGENTS.md
> Single source of truth for AI behavior rules.
> Symlinked into every tool's global config location by `setup.py`.
> Every rule below applies to every agent, every session, without exception.
>
> Agent roles, task flow, and skill routing table are in `instructions/AGENTS-reference.md`.
> The orchestrator loads that file when making routing decisions.

---

<checks>

## DO THIS FIRST — before anything else

<check id="1" name="first-run">
Read the **current project's own** `docs/project-overview/stack.md` (not the shared
`skills/project-overview/` template — that stays generic across every project; see
`decisions/DEC-003`).

If `docs/project-overview/` is missing, or `stack.md` is empty or contains `[XXX]`
placeholders — **stop. Say this:**

> "I need to run first-run analysis before I can help. This will scan the
> codebase and set up the framework. Shall I proceed?"

Then execute all first-run steps before accepting any task.
</check>

<check id="2" name="branch-guard">
If the developer's message requires writing or editing files — create the
branch automatically, no approval needed:

1. Derive the branch name: `<prefix>/<task-name>`.
2. Run `git checkout -b <prefix>/<task-name>` immediately.
3. Tell the developer, after the fact (not a question, just a note):
   > "Created branch `<prefix>/<task-name>`."

Only after the branch exists may any file be written or edited.

Branch prefixes: `feat/` `fix/` `chore/` `refactor/` `docs/` `hotfix/` `release/`
Name rules: lowercase, hyphens only, ≤ 50 chars, derived from the task.
</check>

<check id="3" name="investigate-before-answering">
Never speculate about code you have not opened. If the developer references a
specific file, read it before answering. Investigate relevant files BEFORE
answering questions about the codebase. Never make claims about code before
investigating — give grounded, hallucination-free answers.
</check>

<check id="4" name="commit-push-pr">
Once the current PR's work is done (Steps 6–9 all PASS) — commit, push, and
open the PR/MR automatically. Do not stop for approval first.

1. Run: `git add .` → `git commit -m "<type(scope): description>"`.
2. Load the `pr-provider` skill and run its script (`scripts/open-draft-pr.py`).
   The script — not you — detects the provider (GitHub, GitLab, Azure DevOps),
   pushes the branch, and opens the PR/MR as a draft. Do **not** run `git push`,
   `curl`, or any provider CLI yourself; the script is the only push path.
3. The PR/MR is **always** opened in draft mode. Never open it
   ready-for-review automatically — that stays a manual developer action.
4. Report from the script's `STATUS:` line and exit code, not from assumption.
   If it says the PR/MR must be opened manually (missing token/PAT, unrecognized
   host), the push has still happened — relay its `REASON:` and `URL:` to the
   developer (see `pr-provider`'s "Interpreting the result"). Never ask the
   developer to paste a token into chat.
5. Once the PR/MR exists (or once you've reported why it doesn't), notify
   the developer — this is a notification, not a question, and does not
   wait for a reply:

```
Pushed and opened a draft PR/MR:

Branch:     <current branch> → <base branch>
Commit:     <type(scope): description>
Draft PR/MR: <URL>

Ready for you to review and mark as ready when you're happy with it.
```

Rules:
- `git push --force` is permanently forbidden — not guarded, never allowed
- Never mark the PR/MR ready-for-review and never merge it — those stay manual
- Never echo or log a token/PAT value in any message shown to the developer
- If the developer wants to edit the commit message or PR/MR body afterward,
  they can — it's a draft precisely so it isn't final
</check>

</checks>

---

<rules>

## Non-negotiable rules

<rule id="1" name="git-permissions">
**Allowed (run freely, no developer approval needed):**
`git status`, `git log`, `git diff`, `git branch`,
`git checkout -b` (auto-created per Check 2),
`git add`, `git commit` — auto-run as the completion sequence per Check 4.
Pushing and opening the PR/MR happen **only** through the `pr-provider`
script (`scripts/open-draft-pr.py`), which detects GitHub / GitLab / Azure
DevOps deterministically and always opens a draft. Direct `git push` by the
agent is not permitted.

**Never run under any circumstances:**
`git merge`, `git rebase`, `git reset`, `git push --force`

**One command per bash call — never chain.** Never combine multiple
commands in a single bash tool call using `;`, `&&`, `|`, or any other
shell operator, even when every individual command is separately allowed.
Every agent's permission config matches the full command string, not
command-by-command — a chained call falls through to that agent's `"*"`
fallback (`ask` or `deny`), which fails outright in a headless session
with no one to answer `ask`.

**For checking git status and current branch together**, always call
`powershell -File "$env:USERPROFILE\.config\opencode\scripts\git-context.ps1"`
exactly as written, as a single command, instead of issuing separate or
chained `git status`/`git branch` commands. Use this exact string,
verbatim: `$env:USERPROFILE` (not `~`, which does not reliably expand when
passed as a literal argument to an external process on Windows
PowerShell), double quotes around the path, backslashes as shown. This is
a pre-approved, exact-match command in every relevant agent's permission
list, so it never falls through to the `ask`/`deny` fallback.

For any other git information not covered by that script, issue each git
command as its own separate tool call — never chained.
</rule>

<rule id="2" name="branch-before-write">
No file write or edit until the branch is created. See Check 2.
</rule>

<rule id="3" name="no-third-party-without-approval">
Any dependency add / remove / update — propose and wait for explicit approval.
</rule>

<rule id="4" name="first-run-mandatory">
The current project's own `docs/project-overview/stack.md` contains `[XXX]` or is
missing → run first-run analysis first. (Not the shared `skills/project-overview/`
template — see Check 1 and `decisions/DEC-003`.)
</rule>

<rule id="5" name="show-before-writing">
Always show a plan and get confirmation before writing files.
</rule>

<rule id="6" name="code-principles">
Apply Clean Code, SOLID, KISS, YAGNI to every file.
Conflict resolution: correctness → KISS → YAGNI → SOLID.
</rule>

<rule id="7" name="atomic-changes">
One PR = one concern.
</rule>

<rule id="8" name="skill-loading">
Inside the structured task flow (Steps 1–10 in `orchestrator.md`), skill loading is
handled entirely by each agent's own "Always load" / "Load when relevant" list in
its agent file. Do not additionally consult `skill-rules.json` for these steps —
it would double-load skills the agent already loads deterministically.

Outside that flow — a freeform question or ad-hoc request that hasn't entered the
task flow yet — classify the request and load matching skills from
`skill-rules.json`, highest priority first, capped at `maxMatchesPerRequest`
(see the file's `$config`). Tell the developer which skills were loaded before
starting.
</rule>

<rule id="9" name="post-implementation-pipeline">
After the last file write, before saying "done", run in order:
code-reviewer (lint + security scan + review) → qa → gatekeeper
If any step fails → rework and re-run from code-reviewer.
</rule>

<rule id="10" name="surgical-changes">
Touch only what the task requires. Every changed line traces to the request.
- Do not improve, reformat, or refactor adjacent code
- Do not add docstrings, logging, or annotations not asked for
- Match existing style — do not impose preferences
- Mention unrelated issues; never fix them silently
- Clean up only what your changes made unused
Avoid over-engineering: no extra abstractions, helpers, or flexibility not asked for.
Only validate at system boundaries (user input, external APIs) — trust internal code.
</rule>

<rule id="11" name="no-mcp">
Do NOT use MCP (Model Context Protocol) servers, connectors, or external tool
integrations of any kind. All operations must use only local tools: file read/write,
bash/shell execution within the repo, and git commands within the permitted set.
If a task appears to require MCP, stop and tell the developer — never attempt it.
</rule>

<rule id="12" name="isolated-environment">
Operate only within the current repository directory. Do not reach outside the
repo boundary: no HTTP requests, no external API calls, no cloud service calls,
no writes outside the working directory. The environment is intentionally isolated.
If a task requires external access, stop and flag it to the developer.
</rule>

<rule id="13" name="no-routine-narration">
Do not narrate routine actions. Never say "reading file…", "running tests…",
"checking the codebase…". Report only when starting a new major phase or when
something changes the plan. Every update must state a concrete outcome:
"Found X", "Confirmed Y", "Fixed Z". Silence between tool calls is correct.
</rule>

<rule id="14" name="context-budget-auto-triggers">
Monitor session length. When either threshold is reached, auto-trigger both
`caveman` and `handoff` before the next step — do not wait for the developer:

- Orchestrator has produced **more than 8 agent responses** this session, OR
- Any single response exceeds **~3,000 tokens**

Load `caveman` first (all subsequent output uses compressed mode).
Then load `handoff` and produce the session compact before continuing.
Announce to the developer:
> "Context budget reached. Switching to compact mode and saving a handoff.
> Continuing from: [one-line summary of current step]."
</rule>

</rules>