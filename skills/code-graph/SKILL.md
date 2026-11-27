---
name: code-graph
description: Query the code graph of the project (built by graphify through scripts/graph.py) to find where things are, what calls what and what a change affects, before reading files by hand. Loaded by the architect, the code-reviewer and the implementation agents.
---

## Quick reference

- **Query before you search by hand.** For "where is X", "what calls X", "how does A reach B" and "what does a change to X affect", ask the graph first. It returns a small scoped answer instead of many files.
- **Commands** (one command per bash call, as in AGENTS.md rule 1):
  - `python "$HOME/.config/opencode/scripts/graph.py" query "<question>"`
  - `python "$HOME/.config/opencode/scripts/graph.py" path "<A>" "<B>"`
  - `python "$HOME/.config/opencode/scripts/graph.py" explain "<X>"`
  - `python "$HOME/.config/opencode/scripts/graph.py" update` (re-reads the changed code; builds the graph when there is none)
  - `python "$HOME/.config/opencode/scripts/graph.py" build` (first graph; first-run does it)
- **The orchestrator updates the graph at the start of a task.** Run `update` yourself in a `/review` run, and after you changed files and want to query again.
- **The graph is a map, not the code.** It holds code only, no comments or documents. Read the file before you change it or make a claim about it (AGENTS.md Check 3).
- **No graph, or `STATUS: ERROR`:** say so in one line and use `grep` and `glob` instead. Never block on the graph.
- **Never run graphify yourself.** No `graphify install`, `graphify uninstall`, `graphify hook install` and no other graphify command: they write into AGENTS.md, CLAUDE.md and the tool config folders (DEC-030). Only `scripts/graph.py` runs graphify.
- **Never commit a graph file.** The graph is in `<generated folder>/graphify/`, which ignores itself. If `git status` shows a file from it, stop and tell the orchestrator.
