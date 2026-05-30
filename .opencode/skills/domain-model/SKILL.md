---
name: domain-model
description: Establishes and maintains a shared domain vocabulary (CONTEXT.md) between developers and agents. Loaded during first-run analysis and whenever an agent encounters unfamiliar domain terminology. Prevents agents from using 20 words where 1 precise term will do.
---

# Domain Model

## The problem this solves

At the start of a project, developers and agents are usually speaking different languages. Agents are dropped into a project and asked to figure out the jargon as they go. They use vague generic terms ("component", "service", "handler") where the project has precise domain terms ("Mission", "MFL", "BridgePlugin"). The result is imprecise code, incorrect assumptions, and communication overhead.

A shared domain vocabulary — a `CONTEXT.md` file — fixes this. Once established, every agent reads it before acting. Terminology becomes consistent. The gap between developer intent and agent output shrinks.

---

## CONTEXT.md — what it is

A single file at the project root (or per-repo root in a multi-repo setup) that defines the domain language of the project. It is:

- **A glossary** — precise definitions of domain terms used in the codebase
- **A living document** — updated lazily as new terms emerge during conversations
- **Agent-readable** — written for agents, not for documentation systems

It is **not**:
- A full domain model or UML diagram
- A general README
- A technical architecture doc (that belongs in `docs/architecture.md`)

---

## CONTEXT.md format

```markdown
# Domain Model — [Project Name]

> This file defines the shared vocabulary for this project.
> Agents: read this before making any domain-related decision.
> Developers: update this when a new term is introduced or an existing one is sharpened.

## Core concepts

### [Term]
[One precise definition. What it is, what it is not, how it differs from similar terms.]

### [Term]
[Definition]

## Relationships

[Optional — describe how core concepts relate to each other when the relationship is non-obvious]

## Terms to avoid

| Avoid | Use instead | Reason |
|---|---|---|
| "component" | "[precise term]" | Too generic — ambiguous in this codebase |
| "handler" | "Resolver" | The project uses GraphQL resolvers specifically |
```

---

## When to create CONTEXT.md

Create it during first-run analysis if it doesn't exist. Populate it from:
1. The codebase — class names, package names, API routes, config keys that reveal domain concepts
2. The developer — ask for the 5-10 most important domain terms and their definitions

Ask one term at a time. For each:
> "What does `[term]` mean in this project? In one sentence."

---

## When to update CONTEXT.md

Update it lazily — during normal work, not as a separate task.

**Trigger: a new term appears** that isn't in CONTEXT.md and would be useful to define.
> "I've encountered the term `[X]`. It doesn't appear in CONTEXT.md. Want me to add a definition?"

**Trigger: an existing definition turns out to be fuzzy** — a conversation reveals the term was being used in two different ways.
> "The term `[X]` seems to mean two things. Let me sharpen the definition in CONTEXT.md."

**Trigger: a term from the code doesn't match CONTEXT.md** — the code uses `OrderProcessor` but CONTEXT.md says `PaymentHandler`.
> "The code uses `[X]` but CONTEXT.md defines `[Y]`. Which is canonical?"

Never ask the developer to do a big CONTEXT.md update session. Grow it one term at a time.

---

## Agent rules for using CONTEXT.md

**Before naming anything** (a class, method, variable, file) — check CONTEXT.md. Use the canonical term.

**Before making a domain assumption** — check CONTEXT.md. If the term isn't there, ask.

**When writing tests** — use domain terms in test names and assertions. Tests are domain documentation.

**When the developer uses a term the agent doesn't recognise:**
1. Check CONTEXT.md
2. If not found — ask for a definition before proceeding
3. Add the definition to CONTEXT.md once confirmed

---

## Multi-repo layout

In a multi-repo workspace, there are two patterns:

**Single CONTEXT.md** (most projects) — one file at the workspace root covering the shared domain vocabulary across all repos.

**Per-repo CONTEXT.md** — for repos with genuinely distinct domains (e.g. a voice processing backend and a React frontend have different domain vocabularies). Each repo has its own `CONTEXT.md`. A `CONTEXT-MAP.md` at the workspace root lists where each one lives.

The first-run analysis determines which layout applies and records it in `project-overview`.

---

## Relationship to architecture docs

| CONTEXT.md | docs/architecture.md |
|---|---|
| Domain vocabulary — what things are called | System structure — how things are built |
| Updated lazily during conversations | Updated when architecture changes |
| Written in plain language | Technical diagrams and flows |
| Short — one paragraph per term max | Can be long |

They complement each other. CONTEXT.md answers "what is a Mission?" Architecture docs answer "how is a Mission stored and retrieved?"