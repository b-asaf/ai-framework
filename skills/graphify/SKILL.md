---
name: graphify
description: How to use the graphify code knowledge graph instead of grepping or reading files one by one. Graphify (https://github.com/Graphify-Labs/graphify) builds a local, deterministic call/import graph via tree-sitter — query it for "what calls X", "what connects A to B", or "explain X" before falling back to Read/Glob. Loaded by zoom-out, first-run-analysis, pattern-enforcement, and any agent exploring unfamiliar code.
---

## Quick reference

- **Detection:** `graphify-out/graph.json` present in repo root, or `graphify --version` succeeds
- **Prefer over Read/Glob/grep** for: "what calls X", "what does X depend on", "how do A and B connect", "what does X do"
- **Commands:** `graphify query "<question>"` · `graphify path "A" "B"` · `graphify explain "X"`
- **Building/refreshing:** `python scripts/graphify_smart_viz.py <target-dir>` — for the
  full detail (auto `--code-only` detection, custom `--out`, node-count/viz safety), read
  `references/building-and-refreshing.md`
- **Stale graph:** if `graphify-out/graph.json` is older than the last commit touching source files, run `graphify update .` first
- **Not a replacement for reading the actual diff** — use the graph for orientation and cross-file reasoning, still read the specific file before editing it
- **Zero LLM cost for code parsing** — this is a structural/AST layer, not a judgment layer

# Graphify

Graphify turns the codebase into a queryable knowledge graph (tree-sitter AST, no LLM cost for code) instead of an agent re-deriving structure by reading files. Every edge is tagged `EXTRACTED` (explicit in source) or `INFERRED` (resolved by graphify), so treat `EXTRACTED` edges as fact and `INFERRED` edges as a lead to verify.

## When to use it instead of Read/Glob/grep

| Question shape                                                  | Command                                                      |
| --------------------------------------------------------------- | ------------------------------------------------------------ |
| "What calls / uses / depends on X?"                             | `graphify explain "X"`                                       |
| "How does A relate to B?"                                       | `graphify path "A" "B"`                                      |
| "Where does concept X live and what does it touch?"             | `graphify query "X"`                                         |
| "What are the most central/most-connected pieces of this repo?" | Read the God nodes section of `graphify-out/GRAPH_REPORT.md` |

If graphify is not installed or `graphify-out/graph.json` doesn't exist, fall back to the normal `zoom-out` read sequence — do not block the task on installing it.

## Further reading — load only when the task needs it

| File | Load when |
|---|---|
| `references/building-and-refreshing.md` | Building or rebuilding a graph; using `--out`; understanding auto `--code-only` |
| `references/multi-repo.md` | BE/FE or microservices workspace, cross-service call resolution |
| `references/visualization.md` | Developer wants to manually browse `graph.html`; node-count safety limits |
| `references/staying-in-sync.md` | Setting up a new project (nudge + hooks + commit — see `first-run-analysis` Step 7) |
| `references/relationship-to-skills.md` | How graphify composes with `zoom-out`, `first-run-analysis`, `pattern-enforcement` |