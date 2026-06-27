---
name: zoom-out
description: Lightweight orientation skill. Load at the start of any session on a mature or unfamiliar codebase before writing any code. Builds a mental map of the module structure, entry points, and key boundaries. Takes 2 minutes and prevents 30 minutes of wrong assumptions.
---

# Zoom Out

Before touching anything, understand the shape of what you're working in.

This skill runs fast — it's a structured read, not a deep analysis. The goal is a 1-page orientation map that every subsequent action in the session is grounded in.

---

## When to run

- First session on a new codebase
- First session after a long gap on an existing project
- When dropped into an unfamiliar service or module mid-task
- When `project-overview` exists but the task touches a part of the code you haven't seen yet
- Before running `improve-codebase-architecture`

Do **not** run this if you've already orientated in this session. One zoom-out per session is enough.

---

## The read sequence

Work through these in order. Stop when you have enough orientation — don't read everything.

### 1. Start at the root
```
List the top-level directories and files.
What is the overall shape? (monolith, services, packages, layers)
```

### 2. Find the entry points
For each repo:
- **Backend:** `main()`, `Application.java`, `app.py`, `server.ts`, `cmd/`, `main.go`
- **Frontend:** `main.tsx`, `index.ts`, `App.tsx`, `_app.tsx`, `routes/`
- **Config:** `package.json`, `pom.xml`, `build.gradle`, `pyproject.toml`, `go.mod`

Read the entry point file. Understand what it wires together.

### 3. Identify module boundaries
Scan the directory structure for 2-3 levels deep. Look for:
- Package names / folder names that reveal domain concepts
- Repeated structural patterns (e.g. `controller/service/repository` or `features/X/index`)
- Anything that looks like a public interface between modules

Do not read every file — read the names and infer.

### 4. Check CONTEXT.md
If `CONTEXT.md` exists at the workspace or repo root, read it. Confirm the domain terms match what you're seeing in the code. Flag any mismatch.

### 5. Find where the task lives
Based on the task description, locate the 2-4 files most likely to be relevant. Read their signatures (function/method names, class names) — not the full bodies yet.

---

## Output — orientation map

Produce a short orientation summary before doing anything else:

```
## Zoom-out — [repo name]

### Shape
[One sentence: what kind of codebase this is]

### Entry points
- [file path] — [what it does]

### Module boundaries
- [module/package] — [what it owns]
- [module/package] — [what it owns]
- [module/package] — [what it owns]

### Domain terms (from CONTEXT.md or inferred)
- [term]: [definition or "— infer from usage"]

### Task location
The task likely involves:
- [file or module] — [reason]
- [file or module] — [reason]

### Surprises or gaps
- [anything unexpected, missing, or that contradicts project-overview]
```

Show this to the developer before proceeding. They often correct the surprises row instantly, which saves re-work.

---

## After zoom-out

The orientation map becomes the working context for the session. Reference it when making naming and placement decisions. If the task touches something outside the mapped area, run a targeted zoom-out on that module before proceeding — not a full re-run.

If `CONTEXT.md` is missing or outdated, flag it:
> "CONTEXT.md not found / term X missing. Want me to add it after this session?"

If `project-overview` doesn't match what you're seeing in the code, flag it:
> "project-overview says [X] but the code shows [Y]. Which is current?"