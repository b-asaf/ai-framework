---
name: branching-policy
description: Git branching rules for all agents. Defines branch prefixes, who runs git commands, and what must happen before any file is written.
---

# Branching Policy

## Core rule
**Agents never run git write commands.** The developer handles all git write operations.

Agents may run:
- `git status` — check current branch
- `git log --oneline -10` — review recent history
- `git diff` — inspect changes

Agents must never run:
- `git checkout -b`, `git commit`, `git push`, `git merge`, `git rebase`, `git reset`, `git push --force`

## Branch-before-code rule
No file may be created or modified until the developer confirms a feature branch is open.

**Write guard:** Before calling the `write` or `edit` tool, the agent MUST check whether branch confirmation was obtained from the developer in this conversation. If not confirmed:

1. Halt immediately — do not proceed with any write or edit operation
2. Ask the developer: "Please run: `git checkout -b <prefix>/<task-name>`"
3. Wait for explicit confirmation before continuing

The orchestrator tells the developer exactly what to run:
> "Please run: `git checkout -b feat/your-task-name`"

## Branch naming

| Task type | Prefix | Example |
|---|---|---|
| New feature | `feat/` | `feat/add-user-export` |
| Bug fix | `fix/` | `fix/token-expiry-crash` |
| Chore / maintenance | `chore/` | `chore/update-dependencies` |
| Refactor | `refactor/` | `refactor/payment-service` |
| Documentation | `docs/` | `docs/update-api-contract` |
| Release | `release/` | `release/v2.1.0` |
| Hotfix | `hotfix/` | `hotfix/critical-auth-bypass` |

Branch names should be lowercase, hyphen-separated, and descriptive enough to understand the purpose without reading the PR.

## PR rules
- `main` / `master` is only updated via PR — never directly.
- One PR = one concern (see `atomic-changes` skill).
- At the end of a task, the orchestrator provides the developer with:
  1. A summary of what changed
  2. A suggested commit message following conventional commits: `<prefix>: <description>`
  3. A reminder to push and open a PR

## Commit message format
Follow conventional commits:
```
feat: add user export to CSV
fix: resolve token expiry on refresh
chore: update lodash to 4.17.21
refactor: extract payment logic to service layer
docs: document API contract for /orders endpoint
```