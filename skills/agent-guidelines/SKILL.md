---
name: agent-guidelines
description: Use in every agent's always-load. Output discipline: conclusions first, no routine narration, proportional length, scope limited to the task. Skill loading via skill-rules.json.
---

## Quick reference

- **Output:** conclusions first, no narration of tool calls, proportional length
- **Code output:** output code or diff only — do not explain code unless explicitly asked
- **Scope:** only what the task requires — mention issues outside scope, never fix silently
- **Reading files:** prefer type definitions, interfaces, and function signatures over full implementations. Only read full implementations when the logic itself is what needs to change.
- **Skill loading:** read `skill-rules.json` at task start, load `critical`+`high` matches
- **Context order:** AGENTS.md → skills → agent def → project-overview → task/conversation (static before dynamic — required for prompt caching)
- **Compaction:** > 8 agent responses OR > 3k token response → load `handoff` + `caveman`
# Agent Guidelines

## Output discipline (always applies)

- Lead with the result. Conclusions first, reasoning after if needed.
- Use structured output (tables, checklists, code blocks) over prose.
- Do not re-summarise what previous agents already reported.
- No routine narration of tool calls. Never say "reading file…" or "running tests…".
  Report only when you start a new major phase or discover something that changes the plan.
  Every update must include a concrete outcome: "Found X", "Confirmed Y", "Fixed Z".

## Scope discipline (always applies)

Only do what the current task requires:
- Do not refactor code outside the current PR scope
- Do not "improve" patterns that were not part of the task
- Do not add features not in the spec
- If something problematic is spotted outside scope — note it, never fix it silently

## Skill loading

At task start, read `skills/skill-routing/skill-rules.json`.
Match the developer's message against `keywords` and `intentPatterns`.
Load all matching skills with priority `critical` or `high`.
Tell the developer which skills were loaded and why — one line each.

---

## Reference sections (load on demand)

The sections below are loaded only when the orchestrator or a specific agent needs them.
Do not load all of them upfront — load only the section relevant to the current step.

### [ref: anti-hallucination] Additional verification rules

Beyond Check 3 in AGENTS.md, when working inside a project:
- Never assume a file, class, function, or pattern exists without reading the codebase first.
- Never generate code for an API, schema, or interface without reading the actual definition first.
- Every structural decision must cite its source:
  > ✅ "Following the co-located test pattern found in `src/hooks/useUser.test.ts`"
  > ❌ "The project uses co-located tests" (no source cited)
- If you cannot cite a file or explicit developer decision — treat it as missing, ask.
- When uncertain: use this format before proceeding:
  ```
  ❓ Clarification needed:
  [Specific question]
  [Why it matters for the current task]
  ```

### [ref: context-ordering] Prompt caching order

Assemble context in this order to maximise cache hit rate:
1. AGENTS.md / AGENTS-reference.md (rules — static across all sessions)
2. Skill content (static across all sessions and projects)
3. Agent definition (static across all sessions)
4. project-overview/sub/*.md (project-specific)
5. Task and conversation (changes every turn)

Never place project-specific content before framework content — breaks the cache prefix.

### [ref: context-budget] Session compaction trigger

When either fires, load `handoff` before the next step:
- Orchestrator has produced more than 8 agent responses this session
- Any single response exceeds ~3,000 tokens

Trigger proactively. Do not wait for the session to feel slow.

### [ref: checkpoint-format] Orchestrator checkpoint summary

After each agent completes, produce this before routing forward:

```
## Checkpoint: [step name] — [COMPLETE / BLOCKED]
### Task: [one line]
### Agreed solution: [one line]
### PR: [current PR number and what it contains]
### Completed: [bullets, max 5]
### Decisions: [developer approvals, pattern choices — each with source]
### Handoff to @[next-agent]: [what it needs, files to read first]
```

### [ref: final-summary-format] Orchestrator final task summary

Before routing to @gatekeeper:

```
## Final Task Summary
### Original request: [developer's words]
### Spec: [acceptance criteria, one line each]
### Solution: [what was built, which files changed]
### PR breakdown: | PR | Branch | Status |
### Decisions: | Decision | Chosen | Approved by |
### Open observations: [out of scope items noted for developer]
```
