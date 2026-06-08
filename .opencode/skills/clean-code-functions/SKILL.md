---
name: clean-code-functions
description: Use when writing, modifying, refactoring, or reviewing functions and methods to enforce small, focused, single-purpose code with minimal arguments and clear abstraction levels.
---

# Clean Code — Functions

## Rules

- **Small.** Functions should rarely exceed 20 lines. Most should be under 10. If you need to scroll past a function, it is too long.
- **Do one thing.** A function does one thing if you cannot extract a meaningful sub-function from it. If you need "and" to describe what it does, split it.
- **One level of abstraction per function.** Do not mix high-level orchestration (`processOrder`) with low-level details (`query("SELECT …")`) in the same function body. Read top to bottom as a newspaper narrative.
- **Descriptive names.** A long descriptive name is better than a short cryptic name or a comment. `findUsersByActiveSubscription` beats `getUsers`.
- **Minimal arguments.**
  - 0 args: ideal
  - 1 arg: good
  - 2 args: acceptable
  - 3 args: avoid — use a parameter object instead
  - 4+ args: never
- **No flag arguments.** A boolean parameter announces the function does two things. Split it into two functions.
- **Command-Query Separation (CQS).** A function either *does* something (command — returns void, changes state) or *answers* something (query — returns a value, no side effects). Never both.
- **No hidden side effects.** Functions that appear to query should not secretly mutate state.
- **Extract try/catch bodies.** The body inside `try` and the body inside `catch` should each be a single delegating call to an extracted function. Error handling is its own responsibility.
- **DRY — Rule of Three.** Extract on the third occurrence, not the first or second.

## Write-time checklist

Write the complete function first — do not stop mid-implementation to extract. Once the function is complete and working:
1. Can I state what it does in one phrase without "and"?
2. Are all statements at the same level of abstraction?
3. Does it have 3 or fewer arguments?
4. Does it either return a value *or* change state — but not both?
5. Is any logic here duplicated elsewhere (Rule of Three)?

## Review cite format

`[FUNCTIONS] <file>:<line or function name> — <rule violated and why>`

A function exceeding 20 lines without justification is **NON-BLOCKING** (advisory). A function with a boolean flag argument or a CQS violation is **BLOCKING**.
