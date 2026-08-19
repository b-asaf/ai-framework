# Building / refreshing the graph

Use the wrapper script, not raw `graphify extract`, for any full build or rebuild:

```bash
python scripts/graphify_smart_viz.py <target-dir>
```

This handles three things a raw `graphify extract` call does not:
1. **Auto-detects whether an LLM API key is available** (`GEMINI_API_KEY`, `GOOGLE_API_KEY`, `MOONSHOT_API_KEY`, `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `DEEPSEEK_API_KEY`). If none is set, adds `--code-only` automatically rather than failing partway through on the semantic-extraction step for doc/image files. This is the common case in a closed-model-list corporate environment (see `decisions/DEC-004`) — the code graph itself needs no key at all.
2. **Always runs clustering** (`GRAPH_REPORT.md` + community labels), regardless of repo size — only the HTML visualization is conditionally skipped. See `references/visualization.md`.
3. **Correctly locates `graph.json` even when `--out` is used**, since `cluster-only` has its own independent default that does not know about a custom `extract --out` location — the script always passes `--graph` explicitly rather than relying on that default.

For a lighter incremental update after a small set of changes (no LLM either way):
```bash
graphify update .        # incremental — only changed files, no full rebuild
```

A full `graphify extract .` (bypassing the wrapper) is only needed for advanced flags the wrapper doesn't expose — see `graphify --help` for the full command surface. Inside an interactive agent session you may instead see `/graphify .` and `/graphify . --update` — that's the skill's own in-IDE slash-command form.

## Custom output location

```bash
python scripts/graphify_smart_viz.py <target-dir> --out <output-dir>
```
Writes to `<output-dir>/graphify-out/` instead of `<target-dir>/graphify-out/`. Confirmed via `graphify --help`. The default (output stays inside the repo being scanned) is correct for normal use — reach for `--out` only if you deliberately want graph data centralized somewhere else, e.g. outside the repo entirely.