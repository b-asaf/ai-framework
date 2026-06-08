---
name: code-standards
description: Clean code and SOLID principles applied to every line of code in every agent. Load when implementing, reviewing, or proposing a design. This file is the entrypoint — it links to granular skill files for each dimension.
---

# Code Standards

Apply all four principles to every file written. When principles conflict, resolve in this order:
**correctness → simplicity (KISS) → present requirements (YAGNI) → future extensibility (SOLID)**

## Granular skill files

Each dimension is defined in detail in its own skill file. Load the relevant ones based on the task:

| Skill | Load when |
|---|---|
| `clean-code-naming` | Writing or reviewing any identifier |
| `clean-code-functions` | Writing or reviewing functions or methods |
| `clean-code-comments` | Writing or reviewing code comments |
| `clean-code-classes` | Writing or reviewing classes, interfaces, or modules |
| `clean-code-solid` | Designing or reviewing structure at any scale |
| `clean-code-error-handling` | Writing or reviewing error paths, null handling, exceptions |
| `clean-code-tests` | Writing or reviewing test files |
| `clean-code-security` | Writing or reviewing code that handles external input, auth, or persistence |
| `readability-cognitive-load` | Every implementation and review task |
| `static-code-analysis` | Before any code review begins (precheck gate) |

## Quick reference — always applies

**Names** reveal intent. No abbreviations unless universal (`url`, `id`, `dto`).
Classes: noun. Functions: verb. Booleans: `is`/`has`/`can` prefix.

**Functions** do one thing. Under 20 lines. Max 3 parameters. Return early. No side effects unless the name makes them obvious.

**Structure:** No dead code. No magic numbers — use named constants. No duplication — extract after three occurrences (Rule of Three). Comments explain *why*, not *what*.

**Errors:** Never swallow silently. Fail fast. Typed errors where the language supports it. Never return `null` to indicate failure.

## SOLID — apply at design and review time

For full definitions with write-time checklists and cite formats: read `clean-code-solid`.

Key checks before writing:
- Does each class have one reason to change? (SRP)
- Are dependencies injected, not instantiated? (DIP)
- Is this extended via abstraction rather than modifying existing code? (OCP)

## KISS and YAGNI — apply before adding complexity

For full examples: read `references/kiss-yagni.md`

**KISS pre-write check** — before adding any abstraction, pattern, or layer, ask:
- "Would a senior engineer say this is overcomplicated?" → if yes, simplify
- "Is this the minimum code that solves today's problem?" → if not, cut it
- "Am I adding complexity for a requirement that exists right now?" → if not, it is YAGNI

## Semantic duplication

Catch duplication by meaning, not just by text. Same idea in many places = duplication. Same responsibility with different names = duplication.

**Before writing any new helper, validator, mapper, or workflow — search the codebase first.** Look for existing implementations by intent using domain names, synonyms, nearby modules, similar tests, and related types. If it already exists, reuse or extend it. Do not create a second version of the same idea.

**What counts as duplication:**
- Repeated test setup or mock blocks
- Repeated mapping or normalisation logic
- Repeated validation rules
- Repeated branching for the same business rule
- Repeated error-handling around the same dependency
- New helpers that overlap with existing helpers

**Decision rule:** Reuse when the same problem is already solved. Extract an abstraction when the duplication is real and stable (Rule of Three). Do not extract when similarity is accidental or likely to diverge. Do not hide duplication inside vague `utils` or `helpers` buckets.

**Review cite format:**
`[SEMANTIC DUPLICATION] <file>:<line> — <what is duplicated>, <where similar logic already exists>, <required consolidation>`
`[ABSTRACTION DRIFT] <file>:<line> — <responsibility duplicated outside the proper abstraction>, <where it should live>`

Semantic duplication is **BLOCKING** when the same logic appears in 3+ places. **NON-BLOCKING** (advisory) at 2 occurrences.

## BLOCKING vs NON-BLOCKING — severity model

All code-standards findings fall into one of two categories:

**BLOCKING — must be resolved before PR is approved:**
- Any SOLID violation
- Swallowed exceptions, null returns on failure, exposed vendor exception types
- Magic numbers in domain logic
- Commented-out code
- Security violations (always blocking)
- Fragile tests or tests with no assertion
- Semantic duplication appearing 3+ times
- Any function that does something other than what its name promises (surprise factor)
- Nesting depth > 3 levels
- Boolean expression with > 4 operands

**NON-BLOCKING — advisory, fix when convenient:**
- Naming improvements (unless actively misleading)
- Function length borderline cases (22 lines vs 20)
- Minor comment noise
- Magic numbers in non-domain code (test helpers, config constants)
- Nesting at exactly 3 levels
- Boolean expression with 3–4 operands
- Abstraction mixing that is noticeable but not severe
- Chain length of 4–5 calls
- Line length > 120 characters

## Project patterns take precedence

Check `project-overview` and `CONTEXT.md` first. Consistency within the codebase matters more than theoretical purity. If the project uses a consistent approach that slightly differs from the above, match the project.
