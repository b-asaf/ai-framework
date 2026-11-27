# DEC-030 — Code graph with graphify, run by the framework

**Status:** Accepted
**Date:** 2026-11-26

Supersedes the part of DEC-022 (point 2) and of decision #12 that says the graph is kept current by graphify's own git hooks.

## Context

- DEC-022 removed the old graphify integration and planned a new one (S.13): graphify's hooks keep the graph current, the graph is not committed, a short framework-owned skill, and `setup.py` installs the CLI.
- Probe of 2026-11-26 (graphify 0.9.20, throwaway repositories and a fake home; the real home and the live checkout were unchanged after every step):
  - `extract . --code-only` builds a graph without an API key. `--out DIR` and the variable `GRAPHIFY_OUT` (not in the help) both move `graphify-out/`; `extract` and `update` honor `GRAPHIFY_OUT`, and `query` takes `--graph`.
  - `hook install` writes `post-commit` and `post-checkout` (into `core.hooksPath` when it is set), a `.gitattributes` in the working tree and a merge driver in the local git config pinned to one machine's Python. A commit rebuilds in the background in under 20 seconds, but the hook creates a second graph at `<repo>/graphify-out/` unless `GRAPHIFY_OUT` is in the environment of the commit, and it does nothing in a linked worktree.
  - `graphify install` writes a skill named `graphify` and a `CLAUDE.md` into the home, and `.opencode/` into the current folder. The project installers write sections into `AGENTS.md` and `CLAUDE.md`. `graphify uninstall` did not remove everything that `install` wrote.
  - Check 4 of `AGENTS.md` runs `git add .`, so anything the framework creates in a project must be ignored by git.
- The developer's answers (2026-11-26): the graph lives in a `graphify` subfolder of the framework's folder in the project; the framework writes no husky files.

## Options considered

- **A: graphify's own hooks, as DEC-022 planned.** Rejected: the hook adds a `.gitattributes` that `git add .` would commit, writes a second graph at the repository root, skips linked worktrees, and needs the developer's husky files in repositories with `core.hooksPath`.
- **B: the hooks only where `core.hooksPath` is not set, with `GRAPHIFY_OUT` edited into them.** Rejected: it edits a file graphify generates, still writes the `.gitattributes`, and still misses worktrees.
- **C: the framework runs graphify itself through one script.** Chosen.

## Decision

1. **Location.** The graph is `<generated folder>/graphify/graphify-out/graph.json` (`.ai-framework/graphify/...` by default). The framework creates that folder with a `.gitignore` that holds `*`; it ignores itself too, so nothing from it can be committed.
2. **One script.** `scripts/graph.py` has `build` (`extract --code-only`), `update`, `query`, `path` and `explain`. It reads `generatedDir` through `execution/runner/generated_dir.py`, passes the place to graphify as an absolute `GRAPHIFY_OUT`, and treats a graph file that does not appear as an error. It never runs graphify's `install`, `uninstall` or `hook`.
3. **Who runs what.** First-run builds the graph (Step 3d). The orchestrator runs `update` at the start of a task (Step 1), again after Step 4 when the new branch started from another branch, and in step 1 of the quick lane. The architect, the code-reviewer and the six implementers query it. Each has the allow line `python *scripts*graph.py*` (and `python3`). An error never blocks a task.
4. **Skill.** `code-graph` says when to query and update. Its name cannot be overwritten by graphify's own `graphify` skill.
5. **Never graphify directly.** Agents and the framework do not run `graphify install`, `graphify uninstall`, `graphify hook install` or the platform installers. A test fails if the script names them.
6. **CLI.** `python setup.py` installs graphify with `uv tool install graphifyy` when it is missing (instructions when `uv` is missing), and `--verify` reports the version.
7. **DEC-028 finding.** `backend` now loads `agent-guidelines` like the other five implementers.

## Reasoning

1. **Agent or deterministic?** Deterministic: one script builds and updates, and an agent only chooses when to ask.
2. **Trade-off.** The graph is updated per task and not per commit, so commits made outside a framework session show up at the next task. The time of `update` on a large repository was not measured; it has a 300 second limit, then the task goes on without it. `GRAPHIFY_OUT` is not in graphify's help, so a new version may ignore it; the script then reports an error instead of writing at the repository root.
3. **Cheaper way?** The hooks need no code of ours but need three workarounds (a second graph, a `.gitattributes`, husky files).

## Consequences

- No framework file or text runs graphify's installers. The old `.opencode/plugins/graphify.js` in the live checkout comes from an earlier `graphify install`; the developer may delete it.
- The skills folder has 44 skills.
- A repository with a very large code base may need a longer limit or a manual `build`; that is a later change if the soak shows it.
- Evidence: `tests/test_graph_script.py` (the script, with a stand-in for graphify and real git for the ignore file), `tests/test_setup_graphify.py`, `tests/test_code_graph_text.py` and `tests/test_agent_set.py`.
