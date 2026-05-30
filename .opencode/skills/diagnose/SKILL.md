---
name: diagnose
description: Structured 4-phase debugging loop for finding root causes. Use when facing a bug, unexpected behaviour, or a failing test with an unclear cause. Loaded by backend, frontend, and orchestrator when task type is a bug fix.
---

# Diagnose

Debugging without a signal is guessing. This skill is about finding the signal first, then using it to drive to the root cause systematically. Everything else is mechanical.

---

## Before starting — orient if the codebase is unfamiliar

If you have not worked in this codebase recently, or this is a new session, run `zoom-out` first. Without knowing where the relevant modules live, even Phase 1 (finding the right seam for a signal) takes much longer than it should.

`zoom-out` takes 2 minutes and tells you: where the entry points are, which modules own the relevant domain concept, and what the module boundaries look like. That context makes every subsequent phase faster.

## Phase 1 — Get a signal

**This is the most important phase. Spend disproportionate effort here.**

A signal is a fast, deterministic, agent-runnable pass/fail test that reproduces the bug. If you have one, you will find the cause. If you don't, no amount of staring at code will save you.

Find the signal at the right seam — pick the lowest level that still reaches the bug:

```
Unit test         → fastest, most isolated, best for logic bugs
Integration test  → for bugs that cross layer boundaries
HTTP/curl script  → for API bugs against a running dev server
CLI invocation    → for command-line tools, fixture input → diff output
Replay a trace    → if you have a captured request/response
```

Be aggressive. Be creative. Don't give up until you have a reproducible signal.

**The signal is the spec.** Every subsequent phase is just consuming the signal to narrow down the cause.

---

## Phase 2 — Build a hypothesis list

Before touching anything, list every plausible cause ranked by likelihood. Read the codebase. Use the project's domain glossary (`project-overview` or `CONTEXT.md`) to understand the relevant modules. Check ADRs in the area you're touching.

For each hypothesis:
- State what it predicts
- State what probe would confirm or refute it

Show the ranked list to the developer before probing. They often have domain knowledge that re-ranks instantly ("we just changed #3") or can rule out hypotheses they've already tested.

Don't block on their response — if they're not available, proceed with your ranking.

---

## Phase 3 — Probe systematically

One variable at a time. Each probe must map to a specific prediction from Phase 2.

**Probe tools (in order of preference):**
```
1. Debugger / REPL — one breakpoint beats ten logs
2. Targeted logs at the boundary that distinguishes hypotheses
   → Tag every debug log: [DEBUG-xxxx]. Cleanup becomes a single grep.
   → Never "log everything and grep"
3. Binary bisection — narrow the failing range by half each step
4. Mutation — change one thing, observe if the signal changes
```

After each probe: either confirm a hypothesis, refute it, or narrow the field. Update the ranked list. Never probe the same hypothesis twice.

---

## Phase 4 — Fix, verify, clean up

Once the root cause is confirmed:

1. **Fix at the cause** — not at the symptom. If the bug is in the service layer, fix the service layer. Don't add a guard in the controller.

2. **Write the test first** (if you don't have one from Phase 1). The test must fail before the fix, pass after.

3. **Apply the fix.**

4. **Run the full suite** — not just the new test. The fix must not break existing behaviour.

5. **Remove all debug instrumentation** — every `[DEBUG-xxxx]` log, every temporary breakpoint, every probe mutation. Leave no trace.

6. **Verify the fix end-to-end** — reproduce the original scenario that triggered the bug. Confirm it no longer occurs.

---

## Anti-patterns to avoid

| Anti-pattern | Why it fails |
|---|---|
| Changing code before getting a signal | You're guessing |
| Logging everything | Signal-to-noise ratio becomes useless |
| Fixing the symptom | Bug re-appears elsewhere |
| Probing multiple variables at once | You can't isolate the cause |
| Declaring fixed without running the full suite | You may have broken something else |
| Leaving debug code in | Pollutes the codebase, fails lint |

---

## For bug fix tasks specifically

When the orchestrator routes a bug fix task, load this skill before `pattern-enforcement` or `code-standards`. The first goal is reproducing the bug — conventions come after the root cause is found.

The fix itself then follows TDD: write the failing test first, then the minimal fix to make it pass. See the `tdd` skill.