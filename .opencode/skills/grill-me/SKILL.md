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

## Output

Once all branches are resolved, produce the confirmed spec or HLD. No spec or HLD is written until the grill is complete and the developer has confirmed all decisions.