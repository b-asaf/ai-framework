---
name: code-standards
description: Clean code and SOLID principles applied to every line of code in every agent. Load when implementing, reviewing, or proposing a design.
---

# Code Standards

Apply all four principles to every file written. When principles conflict, resolve in this order:
**correctness → simplicity (KISS) → present requirements (YAGNI) → future extensibility (SOLID)**

## Clean Code — always apply

**Names** reveal intent. No abbreviations unless universal (`url`, `id`, `dto`).
Classes: noun. Functions: verb. Booleans: `is`/`has`/`can` prefix.

**Functions** do one thing. Under 20 lines. Max 3 parameters (use an object beyond that). Return early. No side effects unless the name makes them obvious.

**Structure:** No dead code. No magic numbers — use named constants. No duplication — extract after three occurrences (Rule of Three). Comments explain *why*, not *what*.

**Errors:** Never swallow silently. Fail fast. Typed errors where the language supports it. Never return `null` to indicate failure.

## SOLID — apply at design and review time
For full SOLID definitions: read `references/solid.md`

Key checks before writing:
- Does each class have one reason to change? (SRP)
- Are dependencies injected, not instantiated? (DIP)
- Is this extended via abstraction rather than modifying existing code? (OCP)

## KISS and YAGNI — apply before adding complexity
For full examples: read `references/kiss-yagni.md`

**KISS pre-write check** — before adding any abstraction, pattern, or layer, ask:
- "Would a senior engineer say this is overcomplicated?" → if yes, simplify
- "Is this the minimum code that solves today's problem?" → if not, cut it
- "Am I adding complexity for a requirement that exists right now?" → if not, it's YAGNI

The failure mode is not that patterns are wrong — it's that complexity is added *before it's needed*. Good code solves today's problem simply. Tomorrow's problem gets addressed tomorrow.

## Project patterns take precedence
Check `project-overview` and `CONTEXT.md` first. Consistency within the codebase matters more than theoretical purity. If the project uses a consistent approach that slightly differs from the above, match the project.