# AGENTS.md
> Single source of truth for AI behavior rules.
> Symlinked into every tool's global config location by `setup.py`.
> Every rule below applies to every agent, every session, without exception.
>
> Agent roles, task flow, and skill routing table are in `instructions/AGENTS-reference.md`.
> The orchestrator loads that file when making routing decisions.

---

<checks>

## ⚡ DO THIS FIRST — before anything else

<check id="1" name="first-run">
Read the project's `project-overview` skill file (`sub/stack.md` first).

If it is empty, missing, or contains `[XXX]` placeholders — **stop. Say this:**

> "I need to run first-run analysis before I can help. This will scan the
> codebase and set up the framework. Shall I proceed?"

Then execute all first-run steps before accepting any task.
</check>

<check id="2" name="branch-guard">
If the developer's message requires writing or editing files — **stop first:**

> "Before I make any changes I'll create a branch. I propose:
> `<prefix>/<task-name>`
> Reply 'yes' to confirm and I'll create it, or tell me a different name."

Wait for confirmation. Once confirmed, run `git checkout -b <name>`.
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

<check id="4" name="commit-push-pr-guard">
Before running `git add`, `git commit`, `git push`, or `gh pr create` — stop completely and show the developer:

```
📦 Ready to commit and push. Please review:

Branch:     <current branch>
Files:      <list of changed files>
Commit msg: <type(scope): description>
PR title:   <title>
PR body:    <first 3 lines of body>
Base branch: main

Type 'yes' to proceed, edit the message to change it, or 'cancel' to stop.
```

Rules:
- Never run any of these commands without completing this approval step first
- If the developer edits the commit message, use the edited version exactly
- If the developer says 'cancel' at any point, stop and do not proceed
- `git push --force` is permanently forbidden — not guarded, never allowed
- Run in this exact sequence after approval: `git add .` → `git commit -m "..."` → `git push` → `gh pr create`
- If `gh` is not installed, stop after `git push` and tell the developer to open the PR manually
</check>

</checks>

---

<rules>

## Non-negotiable rules

<rule id="1" name="git-permissions">
**Allowed (run freely):**
`git status`, `git log`, `git diff`, `git branch`,
`git checkout -b` (only after developer confirms — see Check 2)

**Guarded (require explicit developer approval before every run — see Check 4):**
`git add`, `git commit`, `git push`, `gh pr create`

**Never run under any circumstances:**
`git merge`, `git rebase`, `git reset`, `git push --force`
</rule>

<rule id="2" name="branch-before-write">
No file write or edit until the branch is created. See Check 2.
</rule>

<rule id="3" name="no-third-party-without-approval">
Any dependency add / remove / update — propose and wait for explicit approval.
</rule>

<rule id="4" name="first-run-mandatory">
`project-overview` contains `[XXX]` or is empty → run first-run analysis first.
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
