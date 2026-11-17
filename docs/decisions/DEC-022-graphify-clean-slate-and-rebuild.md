# DEC-022 — Graphify: clean slate during the transition, then a new integration

**Status:** Accepted
**Date:** 2026-11-17

## Context

- The developer wants the framework to use graphify: build the graph when work on a repository starts, and update it when changes are made. The only instruction for the transition (2026-11-14, clarified 2026-11-17) is that the existing graphify files may be removed during it, provided the tool is installed and linked properly afterwards.
- The existing implementation (tracked files, `git grep`, 2026-11-17): `skills/graphify/SKILL.md` (715 lines; it looks like graphify's own installed copy, and the ignored `skills/graphify/references/` folder fits that), `scripts/graphify-smart-viz.sh` (136 lines), `install_graphify`, `wire_graphify`, the "Graphify status" block of `--verify` and their calls in `setup.py`, one rule in `skills/skill-routing/skill-rules.json`, text in `skills/first-run-analysis/SKILL.md`, `skills/zoom-out/SKILL.md` and `instructions/CLAUDE.md`, about 15 README lines, and two `.gitignore` lines.
- Defects found while reading: `first-run-analysis` runs `graphify_smart_viz.py` and only a `.sh` file exists; its step 7 commits `graphify-out/` (14.6, 52.1 and 87 MB in the developer's projects); the README says `pattern-enforcement` loads graphify and that skill has no such text.
- Nothing in `tools/`, `tests/`, `execution/`, `hooks/`, `agents/`, `commands/`, `AGENTS.md` or `opencode.json` mentions graphify.
- What the graphify hooks do (their text, read in `garud-poc`): a code-only rebuild with no LLM cost, started detached after each commit and after a branch switch; skipped during a rebase, merge or cherry-pick, and (as read, not run) in a linked worktree.

## Options considered

- **A: keep the implementation and fix it.** The developer asked for a clean slate.
- **B: remove it now and rebuild it as one step.** Chosen.
- **C: drop graphify.** Rejected by the developer: the framework should use it.

## Decision

1. **Clean slate (plan steps S.8b to S.8e), five-PR series with ccusage in S.8a, each under 400 lines:** remove every reference first (S.8b), then delete `scripts/graphify-smart-viz.sh` and `skills/graphify/SKILL.md` from its tail so the frontmatter stays until the last part (S.8c to S.8e); the `.gitignore` lines and the README skill count (45 to 44) go with the last part.
2. **New integration (plan step S.13), developer's answers of 2026-11-17:**
   - The graph is kept current by graphify's own git hooks (`post-commit`, `post-checkout`), installed per project by `first-run-analysis`.
   - The graph output is not committed. Proposed: excluded through `.git/info/exclude`; S.12 may place it in the generated-files folder.
   - A short framework-owned skill says when to build, update and query the graph. It must have a name graphify's own installer cannot overwrite, because `graphify install` writes `skills/graphify/SKILL.md` through the linked skills folder.
   - `setup.py` installs the graphify CLI and `--verify` reports it ("installed and linked properly").
3. **First step of S.13:** read `graphify --help` and test in a throwaway repository: what `graphify hook install` writes, whether a linked worktree rebuilds, whether `GRAPHIFY_OUT` can place the output, and what `graphify install` writes and where (in a fake home first).

## Reasoning

1. **Agent or deterministic?** Deterministic: a hook updates the graph, and an agent only queries it.
2. **Trade-off.** Until S.13 the agents have no graph, and a fresh machine gets no graphify from `setup.py`. The clean slate costs extra churn, accepted by the developer.
3. **Cheaper way?** The hooks already exist in graphify, so the framework writes no rebuild code.
4. **What the developer sees.** A graph that updates after commits without being committed, and a short skill instead of 715 lines.

## Consequences

- The graphify CLI stays installed. Do not run `graphify uninstall`, `uv tool uninstall graphifyy` or `graphify install` until S.13 has tested them. The untracked `.opencode/` folder of the live checkout, `~/.graphify/` and the graphify cache log stay.
- Until S.8b is merged, `python setup.py` and `first-run-analysis` still wire graphify the old way, including a commit of `graphify-out/`.
- The `graphify-out` folders and the `garud-poc` hooks were removed by hand on 2026-11-15. S.13 builds them again.
- The graphify hooks are written by graphify, so the hooks decision (#10, step S.7) does not cover them. They live next to the framework's own hooks, and the names differ.
- Part of this DEC supersedes the graphify parts of DEC-004 and DEC-005; both stay as history.
