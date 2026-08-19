#!/usr/bin/env python3
"""
graphify_smart_viz.py
======================
Cross-platform replacement for graphify-smart-viz.sh — same safety behavior,
but works natively on Windows (no bash/WSL required, which the shell version
needs and which may be blocked by corporate policy — see decisions/DEC-004).

What this does, in order:
  1. Detect whether any LLM API key is set in the environment. If not,
     automatically add --code-only (skips the 26-doc-file semantic
     extraction step that would otherwise fail with "no LLM API key found").
  2. Extract (cheap, always safe, never skipped). Respects --out if given,
     matching graphify's own real flag (confirmed via `graphify --help`):
     "--out DIR   output dir (default: <path>); writes <DIR>/graphify-out/"
  3. Count nodes in the resulting graph.json — read from the correct
     location whether or not --out was used (this is the part the naive
     shell-script port would get wrong: cluster-only has its OWN default
     of <path>/graphify-out/graph.json, which does NOT know about a custom
     --out used during extract — so --graph is always passed explicitly
     below, never left to cluster-only's own default, once --out is used).
  4. Always run clustering (community labels + GRAPH_REPORT.md — needed
     regardless of repo size), passing --no-viz only when over the node
     threshold, so the HTML is the only thing skipped, not the report.

Usage:
    python graphify_smart_viz.py <target-dir> [--out <output-dir>] [extra graphify args...]

Examples:
    python graphify_smart_viz.py .
    python graphify_smart_viz.py [D:\\project-name\\project-backend]
    python graphify_smart_viz.py . --out D:\\graphify-data\\project-backend
    python graphify_smart_viz.py . --update

Override the node threshold: set GRAPHIFY_VIZ_NODE_LIMIT=8000 in the environment.
"""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

NODE_LIMIT = int(os.environ.get("GRAPHIFY_VIZ_NODE_LIMIT", "5000"))

# Every env var graphify itself checks for semantic extraction (per its real
# error message and --extract help: "gemini|kimi|claude|openai|deepseek|ollama
# (default: whichever API key is set)"). If none of these are set, --code-only
# is added automatically rather than letting the run fail partway through.
LLM_KEY_ENV_VARS = [
    "GEMINI_API_KEY", "GOOGLE_API_KEY", "MOONSHOT_API_KEY",
    "ANTHROPIC_API_KEY", "OPENAI_API_KEY", "DEEPSEEK_API_KEY",
]


def has_llm_key():
    return any(os.environ.get(v) for v in LLM_KEY_ENV_VARS)


def extract_out_dir(args):
    """Return the value passed to --out, if present, else None."""
    if "--out" in args:
        idx = args.index("--out")
        if idx + 1 < len(args):
            return args[idx + 1]
    return None


def main():
    args = sys.argv[1:]
    if not args:
        print("Usage: python graphify_smart_viz.py <target-dir> [--out <output-dir>] [extra graphify args...]")
        sys.exit(1)

    target = args[0]
    extra_args = args[1:]

    if not shutil.which("graphify"):
        print("graphify not found on PATH — skipping (see skills/graphify/SKILL.md)")
        sys.exit(0)

    # --- Step 1: decide --code-only automatically ---
    if not has_llm_key() and "--code-only" not in extra_args:
        print("No LLM API key found in environment — adding --code-only "
              "(code call/import graph only, no semantic extraction of docs/images).")
        extra_args = extra_args + ["--code-only"]

    # --- Step 2: extract ---
    print(f"graphify: extracting {target} ...")
    subprocess.run(["graphify", "extract", target] + extra_args, check=True)

    # --- Step 3: locate graph.json correctly, whether --out was used or not ---
    out_dir = extract_out_dir(extra_args)
    base_dir = Path(out_dir) if out_dir else Path(target)
    graph_json = base_dir / "graphify-out" / "graph.json"

    node_count = None
    if graph_json.exists():
        try:
            with open(graph_json, encoding="utf-8") as f:
                data = json.load(f)
            node_count = len(data.get("nodes", []))
        except (json.JSONDecodeError, OSError) as exc:
            print(f"warning: could not read node count from {graph_json}: {exc}")
    else:
        print(f"warning: expected graph.json at {graph_json} but it was not found")

    # --- Step 4: always cluster; skip HTML viz only past the threshold ---
    # --graph is always passed explicitly — never relying on cluster-only's
    # own default, since that default does not know about a custom --out.
    cluster_cmd = ["graphify", "cluster-only", target, "--graph", str(graph_json)]
    if node_count is not None:
        print(f"graph has {node_count} nodes (limit: {NODE_LIMIT})")
        if node_count > NODE_LIMIT:
            print("over threshold — generating GRAPH_REPORT.md, skipping HTML viz")
            cluster_cmd.append("--no-viz")
        else:
            print("under threshold — generating GRAPH_REPORT.md and graph.html")
    else:
        print("could not determine node count — running cluster-only without --no-viz")

    subprocess.run(cluster_cmd, check=True)

    report = base_dir / "graphify-out" / "GRAPH_REPORT.md"
    if report.exists():
        print(f"Done. Report: {report}")
        if node_count is not None and node_count <= NODE_LIMIT:
            html = base_dir / "graphify-out" / "graph.html"
            if html.exists():
                print(f"Visualization: {html}")
    else:
        print("warning: GRAPH_REPORT.md was not produced — check graphify's own output above")


if __name__ == "__main__":
    main()