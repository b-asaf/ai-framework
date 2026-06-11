---
name: agent-guidelines
description: Behavioral rules that every agent must follow to avoid hallucination, manage context effectively, and produce reliable output. Loaded by all agents at the start of every session.
---

# Agent Guidelines

## Anti-hallucination rules

These rules apply to every agent on every task — no exceptions.

### Never assume — always verify
- Never assume a file, class, function, or pattern exists without reading the codebase first.
- Never assume a decision was made without finding it explicitly in the conversation or in `project-overview`.
- Never generate code for an API, schema, or interface without reading the actual definition first.
- If you cannot find the source, say so and ask — do not fill the gap with a plausible guess.

### Cite your source
Every structural decision must be traceable. When following a pattern, naming convention, or architectural choice, reference where it was found:

> ✅ "Following the co-located test pattern found in `src/hooks/useUser.test.ts`"
> ❌ "The project uses co-located tests" (no source cited)

> ✅ "Using `@ControllerAdvice` for error handling, matching `GlobalExceptionHandler.java`"
> ❌ "Spring projects typically use a global exception handler"

If you cannot cite a file or an explicit developer decision, you do not know — treat it as missing and trigger the appropriate discovery or clarification flow.

### Investigate before answering (anti-hallucination — mandatory)

<investigate_before_answering>
Never speculate about code you have not opened. If the developer references a specific
file, read it before answering. Investigate and read relevant files BEFORE answering
questions about the codebase. Never make any claims about code before investigating
unless you are certain — give grounded, hallucination-free answers.
</investigate_before_answering>

When working in a project, always read the relevant existing files before generating
anything. Your training knowledge of a framework or library is a starting point —
the project's actual code is the source of truth. Patterns in the codebase override
general best practice.

### Ask when uncertain
If a requirement, decision, or pattern is ambiguous, ask the developer before proceeding. A short clarifying question is always better than confident wrong output. Use this format:

```
❓ Clarification needed before proceeding:
[Specific question]
[Why it matters for the current task]
```

### Scope discipline
Only do what the current task requires. Do not:
- Refactor code outside the current PR scope
- "Improve" patterns that weren't part of the task
- Add features that weren't in the spec
- Fix unrelated issues noticed while working

If something problematic is spotted outside scope, note it in the output as an observation for the developer — do not fix it silently.

---

## Context management

Long agentic sessions accumulate context. The orchestrator manages this actively — all other agents contribute by keeping their output compact and structured.

### For all agents — output discipline
- Lead with the result, not the reasoning. Put conclusions first.
- Use structured output (tables, checklists, code blocks) over prose where possible.
- Do not re-summarise what previous agents already reported unless directly relevant.
- Keep explanations proportional to complexity — simple tasks get simple responses.

### Skill loading — use skill-rules.json
At the start of every task, read `skills/skill-routing/skill-rules.json` before choosing
which skills to load. This is the authoritative routing table — do not rely on memory or
the task classification table in SHARED-reference.md alone.

Match the developer's message against `keywords` and `intentPatterns` in each rule.
Load all matching skills with priority `critical` or `high` before starting work.
Tell the developer which skills were loaded and why.

### Context budget — proactive compaction
Monitor session length. When either trigger fires, load `handoff` before the next step
and propose compacting the session:

- **Response count:** orchestrator has produced **more than 8 agent responses** this session
- **Token volume:** any single response contains more than **~3,000 tokens** of output

Do not wait for the session to feel slow. Trigger proactively at the threshold.

### For the orchestrator — checkpoint summaries
After each agent completes a step, the orchestrator produces a compact **checkpoint summary** before routing to the next agent. This replaces the full conversation context with a structured state snapshot.

**Checkpoint summary format:**
```
## Checkpoint: [step name] — [COMPLETE / BLOCKED]

### Task
[One line — what the developer asked for]

### Agreed solution
[One line — which option was chosen and why]

### PR breakdown
[Current PR number and what it contains]

### Completed this step
- [What the agent did, in bullet points, max 5]

### Decisions made
- [Any developer approvals, pattern choices, or scope changes — each with source]

### Blockers resolved
- [Any issues that were found and fixed]

### Handoff to: @[next-agent]
- [What the next agent needs to know, specifically]
- [Files it should read before starting]
```

This summary is what gets passed forward — not the full raw agent output. It keeps each agent's working context lean and prevents earlier instructions from being diluted.

### For the orchestrator — final task summary
Before routing to `@gatekeeper`, produce a **final task summary**:

```
## Final Task Summary

### Original request
[Developer's original words]

### Spec (confirmed by developer)
[Acceptance criteria, one line each]

### Solution implemented
[What was built, which files changed]

### PR breakdown
| PR | Branch | Status |
|---|---|---|
| 1 | feat/... | ready to commit |

### Decisions and approvals
| Decision | Chosen | Approved by |
|---|---|---|
| Pattern for X | co-located tests | developer (step 3) |
| New dependency Y | approved | developer (step 4) |

### Open observations (out of scope, for developer awareness)
- [Anything spotted but not fixed]
```

This summary is what the gatekeeper uses to verify all gates — it is the contractual record of the task.
