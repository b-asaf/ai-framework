# Decision log

This folder is the running record of *why* ai-framework looks the way it does. It was
adopted after a separate exploratory project (`Agentic-Development-Flow`) spent significant
effort independently designing an agentic pipeline from scratch, then discovered ai-framework
already solved most of it — more maturely, in production, across real projects. That
project's decision log and verified findings are folded in here rather than kept as a
second, parallel repo. See `DEC-001-adopt-decision-log-process.md` for the full reasoning.

## Why this exists

A framework this capable accumulates real design tradeoffs — which agent handles what,
which checks are deterministic gates vs agentic judgment, what's enforced vs merely
documented. Without a record, those tradeoffs live only in memory or get silently
re-litigated. This folder exists so a future contributor (including a future you) can see
what was decided, why, and what was explicitly rejected — not just what the code currently
does.

## When to add a decision

Any change that:
- adds or removes a skill, agent, or hook
- changes what's enforced deterministically vs left to agent judgment
- changes a threshold, gate, or permission default
- resolves a genuine tradeoff between two reasonable approaches

...gets a short entry here, using `DECISION_TEMPLATE.md`. Small, obvious fixes don't need
one — use judgment; the point is capturing real tradeoffs, not process for its own sake.

## The core question every decision should answer

**Should this be done by an agent, or by deterministic code/config?**

Rule of thumb carried over from the source project: if the same input, run twice, must
produce the same correct answer by inspecting existing state, it belongs in a hook/skill
script (deterministic). If it requires synthesizing something new or resolving ambiguity,
it belongs with an agent — but its output should still be checked by a deterministic gate
before being trusted (`build-verify`/`pre-push` are the existing reference examples of this
pattern).