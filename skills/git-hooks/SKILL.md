---
name: git-hooks
description: Git hook setup and enforcement. Detects hook managers (husky, lefthook, pre-commit), installs hooks, or falls back to plain shell scripts. Loaded by orchestrator during first-run analysis.
---

## Quick reference

- **Three hooks:** `pre-commit` (not on protected branch), `commit-msg` (conventional commits), `pre-push` (cannot push to main/master/develop) — applies to both repos (`[XXX]-be` and `[XXX]-fe`)
- **Detection order:** husky → lefthook → pre-commit → plain shell scripts
- **Plain-script fallback:** scripts live in ai-framework's own `hooks/` folder, not a copy in this skill. If `setup.py` has been run on this machine, they're already wired automatically via git's `init.templateDir` — nothing to do. Otherwise, one-off: `bash <ai-framework>/hooks/install-hooks.sh`
- **After detecting:** tell developer which manager was found and how to install (see `references/manager-installation.md`)
- **If not installed:** warn on every task handoff — "⚠️ Git hooks not installed in [repo]. Branch and commit rules enforced by convention only."

## Orchestrator responsibilities
1. Detect hook manager per repo (see Detection order above)
2. Instruct developer to install using the right method (`references/manager-installation.md`)
3. Instruct developer to run verification steps (same file)
4. Record in `project-overview` under `## Git hooks`
5. If not installed, warn on every task handoff (see Quick reference)