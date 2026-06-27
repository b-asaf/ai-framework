---
name: git-hooks
description: Git hook setup and enforcement. Detects hook managers (husky, lefthook, pre-commit), installs hooks, or falls back to plain shell scripts. Loaded by orchestrator during first-run analysis.
---

# Git Hooks

## What to install
Three hooks in both repos (`[XXX]-be` and `[XXX]-fe`):

| Hook | Enforces |
|---|---|
| `pre-commit` | Not on a protected branch (`main`, `master`, `develop`) |
| `commit-msg` | Conventional commits format |
| `pre-push` | Cannot push to `main`, `master`, or `develop` |

Hook scripts are in `scripts/` in this skill folder.

## Detection order
1. `.husky/` directory or `"husky"` in `package.json` → **Husky**
2. `lefthook.yml` or `"lefthook"` in `package.json` → **Lefthook**
3. `.pre-commit-config.yaml` → **pre-commit**
4. None found → **plain shell scripts**

## After detecting
Tell the developer which manager was found and instruct them to install.
For installation commands: read `references/manager-installation.md`

## Orchestrator responsibilities
1. Detect hook manager per repo
2. Instruct developer to install using the right method
3. Instruct developer to run verification steps (in `references/manager-installation.md`)
4. Record in `project-overview` under `## Git hooks`
5. If not installed, warn on every task handoff:
   > ⚠️ Git hooks not installed in [repo]. Branch and commit rules enforced by convention only.