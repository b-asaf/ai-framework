---
description: Declare a quick fix. Skips clarify, design and plan review; every review, test and gate step still runs. Limited to 3 files and 60 changed lines. Only the developer can use it.
agent: orchestrator
---

Start a quick fix. The developer has declared the fast lane for this task: the text below is the whole spec.

$ARGUMENTS

Follow the section "Invoked via `/quick` - fast lane" in `agents/orchestrator.md` exactly. That file is the
source of truth; this file is a pointer only. If the two ever disagree, orchestrator.md wins and this file
should be corrected to match.
