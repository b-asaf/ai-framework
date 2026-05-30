---
name: documentation
description: When and how to update project documentation. Every agent checks this after completing work. Create docs/ if it does not exist.
---

# Documentation Policy

## When to update docs

After any task, check if the change introduced any of the following:

| Change type | Update required |
|---|---|
| New user-facing flow | Yes |
| New or modified API endpoint or schema | Yes |
| New architectural layer or component | Yes |
| New 3rd party integration | Yes |
| Changed system behavior (startup, config, profiles) | Yes |
| New environment variable or configuration key | Yes |
| Bug fix that changes no behavior | No |
| Test additions or coverage improvements | No |
| Refactor preserving existing architecture | No |
| Style, lint, or formatting changes | No |

## Where docs live

Check `project-overview` for the documentation location. If none is defined:
- Default: `docs/` folder at the repo root
- If `docs/` does not exist, create it

Primary file: `docs/architecture.md`

## docs/architecture.md structure

If creating for the first time:

```markdown
# [Project Name] Architecture

## Overview
[Brief system description]

## System structure
[Repos, how they relate, deployment model]

## Backend architecture
[Layer diagram, key components, data flow]

## Frontend architecture
[Component structure, state, API client]

## API layer
[Endpoints or schema overview]

## Data model
[Key entities and relationships]

## Flows
[One subsection per significant flow, added as they are implemented]

## 3rd party integrations
[External services, SDKs, auth providers]

## Development setup
[How to run locally, required env vars]

## CI/CD
[Pipeline overview, what triggers what]
```

## Agent responsibilities

- `@architect` — update after every approved HLD
- `@backend` / `@frontend` / `@ui` / `@db` / `@api` — flag if their change affects docs
- `@code-reviewer` — flag missing doc update as a WARNING
- `@gatekeeper` — check doc update as a gate
- `@orchestrator` — confirm doc status before final handoff
