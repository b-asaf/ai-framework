---
name: clean-code-classes
description: Use when writing, modifying, refactoring, or reviewing classes, interfaces, and modules to enforce cohesion, size, and organisation. SOLID principles are covered separately in clean-code-solid.
---

# Clean Code — Classes

> SOLID principles (SRP, OCP, LSP, ISP, DIP) are defined in `skills/clean-code-solid/SKILL.md`. This skill focuses on class-level design: size, cohesion, and organisation.

## Rules

- **Classes should be small — measured in responsibilities, not lines.** A class that is hard to name precisely is probably doing too much. If you need "and" to describe it, it is two classes.
- **High cohesion.** Every method in a class should operate on one or more of its instance variables. A class where some methods use one set of fields and other methods use a completely different set is two classes — split them.
- **Organise for change.** Ask "what could cause this class to change?" before finalising it. Each distinct answer is a separate class.
- **No magic numbers.** Every literal that carries domain meaning must be a named constant. `ONE_DAY_IN_MS` explains meaning; `86400000` does not.
- **Avoid negative conditionals.** `if (isActive)` is immediately clear. `if (!isNotActive)` requires two mental inversions. Prefer positive predicates; extract a named boolean if necessary.

## Write-time checklist

Before finalising a class:
1. Can I describe its responsibility in one sentence without "and"?
2. Does every method manipulate at least one of its instance variables?
3. Do any subsets of methods and fields belong together independently? If yes, extract a class.
4. Are all meaningful literals extracted to named constants?
5. Are all conditionals expressed as positive predicates?

## Review cite format

`[CLASSES] <file>:<line or class name> — <what the problem is and why>`

For SOLID violations found during class review, use the SOLID skill format: `[SOLID/<principle>]`.

Magic numbers are **BLOCKING**. Double-negation predicates are **NON-BLOCKING** (advisory).
