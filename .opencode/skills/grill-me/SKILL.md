---
name: grill-me
description: Interview the developer relentlessly about a plan or design until reaching shared understanding, resolving each branch of the decision tree. Use when the developer wants to stress-test a plan, think through a design, or before writing any spec or HLD. If a question can be answered by exploring the codebase, explore it instead of asking.
---

# Grill Me

Interview the developer relentlessly about every aspect of this plan until we reach a shared understanding. Walk down each branch of the design tree, resolving dependencies between decisions one by one.

For each question:
- Ask it alone — one question at a time, never stacked
- Provide your recommended answer based on what you know
- If the question can be answered by exploring the codebase, explore it instead of asking

Do not stop until every branch is resolved and there are no remaining ambiguities.

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

## Output

Once all branches are resolved, produce the confirmed spec or HLD. No spec or HLD is written until the grill is complete and the developer has confirmed all decisions.
