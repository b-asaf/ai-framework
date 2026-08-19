# Staying in sync

As of `decisions/DEC-005`, `first-run-analysis` Step 7 wires all three of the following
automatically for a new project — this section is now primarily reference material for
understanding what happened, or for wiring an already-populated project that predates the
fix.

1. **The always-on nudge**, so the agent prefers the graph over Read/Glob/grep automatically instead of only when it remembers to check: `graphify opencode install` (OpenCode) / `graphify claude install` (Claude Code) / `graphify codex install` / `graphify gemini install`, run from inside the project. This writes the platform's instruction file (`AGENTS.md`/`CLAUDE.md`) plus, on hook-capable platforms, a pre-tool hook that redirects search-style calls toward the graph.
2. **The rebuild hook**, so `graphify-out/graph.json` stays current: `graphify hook install`, also run from inside the project — wires **both a post-commit and a post-checkout hook** (AST-only, zero LLM cost) plus a git merge driver so two people committing in parallel don't leave conflict markers in `graph.json`. Post-checkout means switching branches also triggers a rebuild, not just committing.
3. **Commit `graphify-out/` to git.** This is the step that actually closes the loop on `git pull`/`fetch` — there's no hook for "someone else's commits arrived," so the graph only stays current across a pull if it was already committed and up to date on the pushing end. `first-run-analysis` writes and commits it initially; after that, the post-commit hook keeps updating it locally and it rides along with your normal commits like any other tracked file. If `graphify-out/` isn't committed, every teammate is working from a graph that's only ever as fresh as their own last local commit — pulling never helps.

Recommended `.gitignore` addition in the target project (not this repo) — `graphify-out/cost.json` only; everything else in `graphify-out/` should be committed.

All three are separate from ai-framework's own git template hooks (see `hooks/` and `add_git_template()` in `setup.py`) — install independently and don't conflict.

## If a project predates the DEC-005 automation

Run the three commands above manually, once, inside that project. After that, they're
covered by the hooks/commit pattern the same as any project onboarded after the fix.