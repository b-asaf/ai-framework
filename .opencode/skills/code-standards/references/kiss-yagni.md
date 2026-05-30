# KISS and YAGNI — Reference

## KISS — Keep It Simple, Stupid

The simplest solution that correctly satisfies the requirements is always preferred.

**In practice:**
- Prefer a plain function over a class when state is not needed
- Prefer a direct query over a generic query builder when there is only one use case
- Prefer an `if` statement over a strategy pattern when there are only two branches
- Prefer inline logic over an abstraction that is only used once

**The test:** "Would a new developer understand this in under 2 minutes?" If not, simplify.
Clever code is a liability. Clear code is an asset.

## YAGNI — You Aren't Gonna Need It

Do not build functionality until it is actually required by the current spec.

**The test:** Can this be justified by a current acceptance criterion? If not, it should not be in this PR.

**YAGNI does not mean short-sighted:**
- ✅ Designing a clean interface that is easy to extend later — good architecture
- ❌ Building the extension mechanism before anyone needs it — YAGNI violation

## How all four principles work together

| Principle | Core question |
|---|---|
| Clean Code | Can a developer read and understand this? |
| SOLID | Will this be easy to change when requirements evolve? |
| KISS | Is this the simplest solution that works? |
| YAGNI | Is this required right now? |

**Conflict resolution order:** correctness → simplicity (KISS) → present requirements (YAGNI) → future extensibility (SOLID)