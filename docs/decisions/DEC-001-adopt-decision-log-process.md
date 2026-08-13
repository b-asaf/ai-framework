# Decision: Adopt a decision log; merge Agentic-Development-Flow into ai-framework

**Date:** 2026-08-05
**Status:** accepted

## Context
A separate project, `Agentic-Development-Flow`, was started to design a headless, ATDD-based
agentic coding pipeline from scratch — project structure detection, language adapters,
Gherkin planning, a mandatory human approval gate, strict TDD enforcement, mutation testing,
a CRAP-score risk gate, and an engine adapter layer over OpenCode. Over roughly 18 design
decisions, several were verified through real smoke testing (OpenCode's actual headless
contract, real vitest/Surefire JSON/XML output shapes, corporate Maven `settings.xml`
requirements, prompt-cache cost behavior).

A subsequent review found that ai-framework already solves most of this, more maturely and
in production use across real projects: `first-run-analysis` + `.ai-framework.json` (project
command discovery), `repo-topology` (monorepo/multi-repo/hybrid detection, exceeding the
scope of the source project's design), `AGENTS.md` + `skill-routing` (convention
enforcement), `build-verify` + `pre-push` (a two-layer deterministic enforcement pattern the
source project didn't have), `product-manager`/`plan-reviewer` (requirements clarification
and an agentic pre-implementation gate), and `tdd`/`atomic-changes` (matching the source
project's TDD and vertical-slice philosophy closely).

## Options considered
- A: Keep both repos — ai-framework as the executable framework, Agentic-Development-Flow as
     a separate spec/decision-log repo, cross-referenced
- B: Merge fully — retire Agentic-Development-Flow, carry its still-valuable contributions
     and its decision-log process into ai-framework directly — chosen

## Decision: Option B
A full reconciliation pass classified every decision from the source project as: already
covered (no action), extends something existing (modify), or genuinely new (build). Most
were already covered, several more maturely than originally designed. What remained
genuinely new or extending: CRAP score (new), mutation testing (new), a deterministic
diff-size backstop for atomic-changes enforcement (new), cross-family per-stage model
config validation (extends existing per-agent `model:` fields), ADO/GitLab PR support
(extends `code-reviewer`'s current GitHub-only capability), a git-auth pre-flight check
(new, small), and a headless entry point (new — the most significant piece, resolved as a
three-phase model: interactive clarification via existing `product-manager`, headless
execution with reversibility-tiered git permissions, manual-only PR approve/merge).

The source project's decision-log discipline (Principle Gate: agent-vs-deterministic,
cost/simplicity tradeoffs, explicit rejected alternatives) is adopted here as `docs/decisions/`,
becoming how ai-framework itself evolves going forward, not a one-time migration artifact.

## Reasoning
1. Agent or deterministic? This decision is itself neither — it's a process/organizational
   choice. The process it establishes exists specifically to keep making that distinction
   explicit for every future change.
2. Trade-off: maintaining two repos costs ongoing sync effort with no clear benefit once the
   reconciliation showed most of the source project's design was already covered; a single
   repo is simpler and matches how ai-framework is actually consumed by real projects today.
3. Cheaper alternative: doing nothing (leaving the source project's findings undocumented)
   was rejected — several findings (real OpenCode headless contract behavior, real
   vitest/Surefire output shapes, the settings.xml corporate-repository pattern) are
   genuinely useful operational knowledge that cost real effort to verify and would
   otherwise be lost.
4. Visibility gained: future contributors can see why a gate exists or a threshold is set
   where it is, not just that it exists.

## Consequences
- `Agentic-Development-Flow` is archived (not deleted) with a pointer to this decision, once
  the remaining genuinely-new items are migrated.
- Every subsequent addition to ai-framework that changes a gate, threshold, or agent/skill
  boundary should get a short entry here.
- The specific new/extended items identified above are tracked as their own decisions as
  they're built, not bundled into this one.