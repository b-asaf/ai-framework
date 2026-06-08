---
name: clean-code-naming
description: Use when writing, modifying, refactoring, or reviewing code to enforce intention-revealing, unambiguous names for variables, functions, classes, interfaces, tests, and files. Load alongside code-standards on every implementation and review task.
---

# Clean Code — Naming

## Rules

- **Reveal intent.** A name must answer why something exists, what it does, and how it is used. If a name requires a comment to understand, rename it.
- **Avoid disinformation.** Never use names that mislead. `accountList` must be a list; if it is a set or map, say so. Avoid names that differ only in subtle ways.
- **Make meaningful distinctions.** `ProductInfo`, `ProductData`, and `Product` as siblings are noise. Name the difference, or remove one. Never use `a1`, `a2`, `a3`.
- **Use pronounceable names.** If you cannot say it, you cannot discuss it — `generationTimestamp` not `genymdhms`.
- **Use searchable names.** Single-letter names are only acceptable as loop counters in very short blocks. `MAX_RETRIES` not bare `3`.
- **Avoid encodings.** No Hungarian notation, no `I` prefix on interfaces, no `Impl` suffix.
- **Class names are nouns.** `Customer`, `OrderProcessor`, `AddressParser`. Never `Manager`, `Data`, `Info`, `Handler` as standalone names — they say nothing.
- **Method names are verbs.** `save`, `getUser`, `isEligible`, `deleteExpiredSessions`.
- **Booleans use `is` / `has` / `can` prefix.** `isActive`, `hasPermission`, `canDelete`.
- **One word per concept.** Pick `fetch`, `retrieve`, or `get` — use it consistently everywhere.
- **Use domain language.** Prefer terms from `CONTEXT.md` and `project-overview` for business concepts. Prefer well-known CS terms (`Queue`, `Visitor`, `Factory`) for technical concepts.
- **Include units in numeric names.** Any numeric parameter, variable, or field whose value is meaningless without knowing its unit must include the unit in its name. `durationInMs`, `timeoutInSeconds`, `offsetInDays`, `ratePerSecond`, `thresholdInPercent`. A bare `int duration` or `long timeout` forces every caller to consult the docs or the source.
  - Exempt: loop counters, collection sizes, array indices, and booleans.
  - Applies to: method parameters, local variables, fields, and constants.
- **Avoid mental mapping.** Readers should never need to translate `r` into "the url after stripping the host". Names encode meaning directly.

## Write-time checklist

Before finalising any name:
1. Does it reveal *why* and *what* without needing a comment?
2. Could it be confused with something else in this codebase?
3. Can a new team member understand it in 5 seconds?
4. Is it consistent with how the same concept is named elsewhere?
5. If it is a numeric value — does the name include the unit? (`durationInMs` not `duration`)

## Review cite format

`[NAMING] <file>:<line> — <what the name is, what it actually means, what it should be renamed to>`

Examples:
- `[NAMING] SchedulerService.java:34 — parameter 'delay' should be 'delayInMs' (unit is ambiguous)`
- `[NAMING] OrderRepository.java:12 — 'accountList' is a Set, not a List; rename to 'accountSet'`

Naming findings are **NON-BLOCKING** unless the name is actively misleading (contradicts what the code does) or a numeric name is missing its unit — in that case it is **BLOCKING**.
