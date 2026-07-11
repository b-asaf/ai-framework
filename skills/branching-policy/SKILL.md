---
name: branching-policy
description: Git branching rules, branch naming conventions, and PR handoff format. Git permission rules (what agents can and cannot run) are defined in AGENTS.md Rule 1 — do not duplicate them here.
---

# Branching Policy

> Git permission rules (allowed/forbidden commands) are in AGENTS.md Rule 1.
> This skill covers naming, conventions, and handoff format only.

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

Branch names: lowercase, hyphen-separated, descriptive enough to understand without reading the PR.

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
