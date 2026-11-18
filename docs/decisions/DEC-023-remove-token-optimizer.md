# DEC-023 — Remove Token Optimizer from the framework

**Status:** Accepted
**Date:** 2026-11-18

## Context

- The developer decided on 2026-11-18 to remove Token Optimizer (plan step S.8f).
- What exists (tracked files, `git grep`, 2026-11-18): `TOKEN_OPTIMIZER_REPO`, `install_token_optimizer` and `audit_token_optimizer` in `setup.py`, called as step 4 of `main`; a README section "Token usage reduction", a line in the setup description, a sample output block and two table rows; a table in `docs/session-summary.md`. No agent, skill, command, hook, test or tool calls it.
- Token Optimizer is a third-party Claude Code plugin (`alexgreensh/token-optimizer`). The README states that it is licensed under PolyForm Noncommercial 1.0.0 (free for personal, research and educational use, commercial use needs a separate license from the author). The developer's environment is described as corporate in DEC-004; the license was not assessed here.
- On Windows `setup.py` only clones the repository and prints a hint; it never runs the installer. On this machine the clone is in `~/.claude/token-optimizer/` (54 MB, v5.13.0), the skill is not linked, no plugin is installed and `~/.claude/settings.json` does not mention it. On Mac and Linux `setup.py` runs `bash install.sh` from the unpinned clone.
- Published claims of savings trace back to the tool's own README; no independent check was found. Claude Code compacts context on its own. The framework's runner takes tokens and cost from the RunRecords (plan decision #6).

## Options considered

- **A: keep it.** Installs third-party code during setup, with a license that restricts commercial use, for a tool that is not wired in.
- **B: delete it.** Chosen.

## Decision

Delete `TOKEN_OPTIMIZER_REPO`, `install_token_optimizer`, `audit_token_optimizer` and their calls in `setup.py` (renumber the step comment after them), the README passages, and the table of `docs/session-summary.md`. One PR (plan step S.8f). Older mentions in `CHANGELOG.md` and earlier decisions stay as history.

## Reasoning

1. **Agent or deterministic?** Neither: this removes an unused installer.
2. **Trade-off.** A developer who wants a context audit in Claude Code can install the plugin on their own.
3. **Cheaper way?** Keeping it costs setup code that has no tests (plan step 5.3) and a license question.
4. **What the developer sees.** A shorter `setup.py` and a README without a tool the framework does not use.

## Consequences

- The clone in `~/.claude/token-optimizer/` stays on the machine until the developer deletes it.
- The PR keeps the output of `python setup.py --verify` unchanged except for any Token Optimizer lines.
