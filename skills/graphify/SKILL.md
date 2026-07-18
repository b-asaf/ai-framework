---
name: graphify
description: How to use the graphify code knowledge graph instead of grepping or reading files one by one. Graphify (https://github.com/Graphify-Labs/graphify) builds a local, deterministic call/import graph via tree-sitter — query it for "what calls X", "what connects A to B", or "explain X" before falling back to Read/Glob. Loaded by zoom-out, first-run-analysis, pattern-enforcement, and any agent exploring unfamiliar code.
---

## Quick reference

- **Detection:** `graphify-out/graph.json` present in repo root, or `graphify --version` succeeds
- **Prefer over Read/Glob/grep** for: "what calls X", "what does X depend on", "how do A and B connect", "what does X do"
- **Commands:** `graphify query "<question>"` · `graphify path "A" "B"` · `graphify explain "X"`
- **Stale graph:** if `graphify-out/graph.json` is older than the last commit touching source files, run `graphify . --update` first
- **Visualization:** never open `graph.html` directly for large repos — use `scripts/hooks/graphify-smart-viz.sh` (auto-skips HTML past ~5000 nodes)
- **Not a replacement for reading the actual diff** — use the graph for orientation and cross-file reasoning, still read the specific file before editing it
- **Zero LLM cost for code parsing** — this is a structural/AST layer, not a judgment layer; see "Relationship to other skills" below for what it doesn't replace

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

## Building / refreshing the graph

```bash
graphify . --update      # incremental — only changed files, no full rebuild
graphify .                # full rebuild — only needed on first run or after --force is warranted
```

Prefer `--update` for anything mid-project. A full rebuild is a first-run or explicit-request action only.

## Multi-repo workspaces (BE/FE or microservices)

Run graphify per repo, then merge into one workspace-level graph so cross-service calls (e.g. FE fetch → BE endpoint) resolve:

```bash
graphify [xxx]-be --as be
graphify [xxx]-fe --as fe
graphify global add [xxx]-be/graphify-out/graph.json --as be
graphify global add [xxx]-fe/graphify-out/graph.json --as fe
```

## Visualization and node-count safety

`graph.html` becomes unusable past roughly 5000 nodes and is never needed for agent reasoning — only for a developer manually browsing the graph. Always build through `scripts/hooks/graphify-smart-viz.sh` rather than calling `graphify` directly when a visualization might be wanted; the wrapper extracts with `--no-viz` first, checks the node count, and only regenerates HTML (via `--cluster-only`) when it's under the threshold. See that script for the exact logic.

## Staying in sync

`graphify hook install` wires a post-commit hook that keeps `graphify-out/graph.json` current automatically (AST-only, zero LLM cost). This is separate from ai-framework's own git template hooks (see `hooks/` and `add_git_template()` in `setup.py`) — both install independently and don't conflict.

## Relationship to other skills

- **`zoom-out`** — runs a manual read sequence for orientation. If graphify is available, its Step 1–3 (root structure, entry points, module boundaries) should be answered from `graphify-out/GRAPH_REPORT.md` and `graphify explain` first, falling back to manual reads only for what the graph doesn't cover.
- **`first-run-analysis`** — Step 4 (convention detection) currently scans 10–20 representative files. When graphify is available, seed that scan from the graph's cross-file `calls`/`imports`/`inherits` edges instead of sampling, then confirm patterns against the actual files found. Graphify does not replace this step's LLM judgment (is the convention good, is it consistent, does it belong in `docs/refactoring-plan.md`) — it only replaces how the input is gathered.
- **`pattern-enforcement`** — before proposing where a new file/class/component goes, check `graphify query "similar to X"` for existing analogous structures instead of relying on memory of the last few files read.

Do not duplicate content between graphify's structural output and skill-authored narrative docs (`project-overview`, `CONTEXT.md`). Graphify answers "what connects to what"; `project-overview`/`CONTEXT.md` answer "why" and business rules. Link to graphify queries from those docs rather than re-describing the graph in prose.
