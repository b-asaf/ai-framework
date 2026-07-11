---
name: grill-me
description: Use when requirements or design are ambiguous, unconfirmed, or untested. Grills the developer one question at a time to resolve every branch of the decision tree before any spec or HLD is written.
---

## Quick reference

**Before grill:** six-rung necessity check — does this need to exist? stdlib? native platform? installed dep? one line? Only then: grill.

**Grill rules:** one question at a time, provide recommended answer, explore codebase before asking.

**Domain hygiene:** challenge terminology vs CONTEXT.md, update CONTEXT.md inline as terms crystallise.

**ADR gate:** offer ADR only when all three true — hard to reverse + surprising without context + real trade-off.

**Output:** confirmed spec or HLD only after every branch resolved and developer confirms.
# Grill Me

Interview the developer relentlessly about every aspect of this plan until we reach a shared understanding. Walk down each branch of the design tree, resolving dependencies between decisions one by one.

For each question:
- Ask it alone — one question at a time, never stacked
- Provide your recommended answer based on what you know
- If the question can be answered by exploring the codebase, explore it instead of asking

Do not stop until every branch is resolved and there are no remaining ambiguities.

## Before the grill — necessity check (always run first)

Before asking any requirement or design question, run this six-rung check against
the request. Stop at the first rung that holds and surface it to the developer:

1. **Does this need to exist at all?** → Does the user need X, or does Y (an existing
   feature, a config option, a simpler workflow) already cover it?
2. **Does the standard library already do this?** → Check the language's stdlib before
   assuming a new implementation is needed.
3. **Does a native platform feature cover it?** → e.g. `<input type="date">` before
   installing a date picker library.
4. **Does an already-installed dependency solve it?** → Search the existing `package.json`
   / `build.gradle` / `pom.xml` before proposing a new one.
5. **Can this be one function or one line?** → If yes, that is the implementation.
6. **Only then:** proceed to the full grill.

When a rung holds, say it directly:
> "Before we go further — [existing feature / stdlib / installed dep] already covers this.
> Do you still want to build a custom solution, and if so, why?"

Wait for the developer's answer. If they confirm they still want to proceed, continue
to the grill. This check is not a blocker — it is a forcing function to surface
cheaper alternatives before effort is committed.

**Never silently skip this check.** The most expensive code is the code that gets
built, reviewed, and maintained when it never needed to exist.

## For requirements (product-manager)

Cover: what problem, who is affected, what does done look like, what is out of scope, what are the edge cases, what is the acceptance test.

## For design (architect)

Cover: does this pattern already exist in the project (check first), which layer owns what, does this introduce a new dependency (needs approval), can this be broken into atomic PRs, how will it be tested.

## During the grill — domain model hygiene

While grilling, actively use and maintain the domain vocabulary in `CONTEXT.md`:

**Challenge terminology conflicts.** When the developer uses a term that conflicts with the existing language in `CONTEXT.md`, call it out immediately:
> "Your glossary defines 'cancellation' as X, but you seem to mean Y — which is it?"

**Sharpen fuzzy language.** When the developer uses vague or overloaded terms, propose a precise canonical term:
> "You're saying 'account' — do you mean the Customer or the User? Those are different things in CONTEXT.md."

**Cross-reference with code.** When the developer states how something works, check whether the code agrees. If you find a contradiction, surface it:
> "Your code cancels entire Orders, but you just said partial cancellation is possible — which is right?"

**Update CONTEXT.md inline.** When a term is resolved during the grill, update `CONTEXT.md` right there — do not batch these up. Capture them as they crystallise. CONTEXT.md is a glossary only — no implementation details.

**Stress-test with scenarios.** When domain relationships are being discussed, invent specific edge-case scenarios that force the developer to be precise about boundaries between concepts.

## During the grill — ADR offers

Offer to write an Architecture Decision Record only when all three criteria are true:

1. **Hard to reverse** — the cost of changing your mind later is meaningful
2. **Surprising without context** — a future reader will wonder "why did they do it this way?"
3. **Real trade-off** — there were genuine alternatives and one was chosen for specific reasons

If any of the three is missing, skip the ADR. When all three apply, say:
> "This decision meets the ADR bar — hard to reverse, non-obvious, and a real trade-off. Want me to record it in `docs/adr/`?"

ADR location: `docs/adr/NNNN-short-title.md`. Create `docs/adr/` if it doesn't exist. Only create the file after the developer confirms.

## Completion criterion

The grill is complete when **every** of the following is true:
- Every branch of the decision tree has a confirmed answer (developer said yes/approved/confirmed)
- No question remains unanswered or marked "to be decided later"
- The domain model (`CONTEXT.md`) is consistent with all confirmed decisions
- Any ADR decisions meeting the three-criteria bar have been offered and either written or declined

Only then: produce the confirmed spec or HLD.

## Output

Once all branches are resolved, produce the confirmed spec or HLD. No spec or HLD is written until the grill is complete and the developer has confirmed all decisions.
