---
name: handoff
description: Compact the current conversation into a handoff document so a fresh agent can continue the work without losing context. Use when a session is getting long, switching agents, or ending a work session mid-task.
---

# Handoff

When a session grows long, context degrades. Earlier decisions get diluted. A fresh agent starting mid-task without context makes wrong assumptions. The handoff document fixes this — it's a structured snapshot that lets any agent (or the same agent in a new session) pick up exactly where things left off.

## When to use

- Session is getting long and responses are slowing down
- Switching from one primary agent to another mid-task
- Ending a work session with unfinished work
- Before invoking `@gatekeeper` on a complex multi-PR task
- Developer asks to "save progress" or "wrap up"

## What to write

Save to a temp file path: use a name like `.handoff-[task-slug]-[date].md` in the project root.

```markdown
# Handoff — [task name]
Date: [date]
Session: [brief description of what this session was doing]

## Current state
[One paragraph: where things stand right now. What's done, what's in progress, what's blocked.]

## Original task
[The developer's original request, verbatim or closely paraphrased]

## Confirmed decisions
[Bullet list of every decision that was made and confirmed by the developer.
 Each decision cites where it was confirmed: "developer confirmed in step 3".]

## Work completed
[What was implemented, tested, or reviewed. File paths where relevant.]

## Work remaining
[What still needs to happen to finish the task. In order.]

## Open questions
[Anything unresolved that needs developer input before work can continue.]

## Skills to load in next session
[Which skills the next agent should load immediately.]

## Files to read first
[The 3-5 most important files for a fresh agent to read before doing anything.]

## Do not
[Any specific pitfalls, constraints, or things the next agent must not do,
 based on what was learned in this session.]
```

## Rules

**Do not duplicate** content already captured in other artefacts. Reference them instead:
- PRD → link to the GitHub issue or file path
- Plan → link to the plan file
- ADRs → link to `docs/adr/`
- Diffs → reference the branch name
- Test results → reference the test run output

**Be specific about file paths.** "The service layer" is not useful. `src/services/MissionService.java` is.

**Record what failed**, not just what succeeded. If an approach was tried and didn't work, say so — the next agent will waste time trying the same thing.

**Keep it short.** The handoff document should be readable in 2 minutes. If it's longer, you're duplicating instead of referencing.

## After writing

Tell the developer:
> "Handoff saved to `.handoff-[task-slug].md`. Start a new session and say: 'Continue from handoff — read `.handoff-[task-slug].md` first.'"