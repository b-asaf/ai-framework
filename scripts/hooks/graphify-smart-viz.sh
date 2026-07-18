#!/bin/sh
# graphify-smart-viz.sh
# ----------------------
# graphify has no built-in node-count threshold for skipping HTML generation —
# graph.html just becomes unusably large/slow past ~5000 nodes. This wrapper
# adds that threshold automatically:
#
#   1. Extract with --no-viz (cheap, always safe, never skipped)
#   2. Count nodes in the resulting graph.json
#   3. Only if the graph is under the threshold, regenerate with the HTML
#      visualization via --cluster-only (reuses the existing graph — no
#      re-extraction, so this costs nothing extra beyond one clustering pass)
#
# Usage:
#   scripts/hooks/graphify-smart-viz.sh <target-dir> [extra graphify args...]
#
# Example:
#   scripts/hooks/graphify-smart-viz.sh .
#   scripts/hooks/graphify-smart-viz.sh ./my-service --update

set -eu

TARGET="${1:-.}"
shift || true
EXTRA_ARGS="$@"

# Override with GRAPHIFY_VIZ_NODE_LIMIT=8000 scripts/hooks/graphify-smart-viz.sh . etc.
NODE_LIMIT="${GRAPHIFY_VIZ_NODE_LIMIT:-5000}"

if ! command -v graphify >/dev/null 2>&1; then
  echo "graphify not found on PATH — skipping (see skills/graphify/SKILL.md)"
  exit 0
fi

echo "graphify: extracting (no-viz) for $TARGET ..."
graphify extract "$TARGET" $EXTRA_ARGS

GRAPH_JSON="graphify-out/graph.json"
if [ ! -f "$GRAPH_JSON" ]; then
  # Some invocations write into a target-relative graphify-out/ — check there too
  ALT="$TARGET/graphify-out/graph.json"
  if [ -f "$ALT" ]; then
    GRAPH_JSON="$ALT"
  fi
fi

if [ ! -f "$GRAPH_JSON" ]; then
  echo "graphify: could not locate graph.json after extraction — skipping viz step"
  exit 0
fi

NODE_COUNT=$(python3 - "$GRAPH_JSON" <<'PY'
import json, sys
try:
    with open(sys.argv[1]) as f:
        data = json.load(f)
    nodes = data.get("nodes", [])
    print(len(nodes))
except Exception:
    print(-1)
PY
)

if [ "$NODE_COUNT" -lt 0 ]; then
  echo "graphify: could not parse node count from $GRAPH_JSON — skipping viz step"
  exit 0
fi

echo "graphify: $NODE_COUNT nodes"

if [ "$NODE_COUNT" -le "$NODE_LIMIT" ]; then
  echo "graphify: under limit ($NODE_LIMIT) — generating HTML visualization"
  graphify cluster-only "$TARGET" $EXTRA_ARGS
else
  echo "graphify: $NODE_COUNT nodes exceeds limit ($NODE_LIMIT) — skipping HTML, use the CLI/JSON instead"
  echo "  graphify query \"...\"   graphify path \"A\" \"B\"   graphify explain \"X\""
fi
