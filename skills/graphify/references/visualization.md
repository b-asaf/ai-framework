# Visualization and node-count safety

`graph.html` becomes unusable past roughly 5000 nodes and is never needed for agent reasoning — only for a developer manually browsing the graph. `scripts/graphify_smart_viz.py` handles this automatically: it always runs clustering (so `GRAPH_REPORT.md` and community labels are produced either way) and only adds `--no-viz` to skip the HTML once the repo is over the threshold.

Override the threshold for one run:
```bash
set GRAPHIFY_VIZ_NODE_LIMIT=10000    # Windows
export GRAPHIFY_VIZ_NODE_LIMIT=10000 # bash
python scripts/graphify_smart_viz.py <target-dir>
```
`set` (Windows) only lasts for the current terminal session. To reset explicitly without closing the window: `set GRAPHIFY_VIZ_NODE_LIMIT=`.

Raising the limit above the actual node count does not guarantee a pleasant experience — the ~5000 figure is a real usability limit in the browser, not an arbitrary guess. Prefer `GRAPH_REPORT.md` (always generated, text-based, no size limit) unless a visual is specifically needed.

**Windows note:** the original shell wrapper (`scripts/graphify-smart-viz.sh`) requires `bash`, which may be blocked by corporate policy (confirmed case — see `decisions/DEC-004`). `graphify_smart_viz.py` is the cross-platform equivalent and is the recommended default on any platform, not just Windows — it only depends on Python, which `setup.py` already requires.