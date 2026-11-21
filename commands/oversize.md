---
description: Approve a branch that is over the changed-lines limit, as one PR or split into several. Run it after a push was blocked for size. Only the developer can use it.
agent: orchestrator
---

Handle a branch that is over the changed-lines limit. The developer has declared this exception: the text below is the reason.

$ARGUMENTS

Follow the section "Invoked via `/oversize` - reviewed size exception" in `agents/orchestrator.md` exactly. That file is the
source of truth; this file is a pointer only. If the two ever disagree, orchestrator.md wins and this file
should be corrected to match.
