---
name: readability-cognitive-load
description: Use when writing or reviewing code to measure and reduce the mental effort required to read it. Evaluates nesting depth, boolean complexity, working memory load, abstraction consistency, and surprise factor. Load alongside code-standards on every implementation and review task.
---

# Readability & Cognitive Load

Cognitive load is the total mental effort required to read, understand, and reason about code. High cognitive load increases defect rate and slows maintenance. This skill measures the reader's burden — not correctness, not architecture — purely: *how hard is this to understand in one focused pass?*

The goal is code a qualified developer can read and fully understand **within one focused pass**, without backtracking, without consulting other files, and without holding more than five to seven things in working memory at once.

---

## Dimension 1 — Nesting Depth

**Maximum 2 levels** of nesting inside a function body. Each additional indentation level multiplies the mental stack the reader must maintain.

Resolution: invert conditions into guard clauses; extract nested blocks into named functions.

```
// Bad — 3 levels
function process(order) {
  if (order.isValid()) {
    if (order.hasItems()) {
      for (const item of order.items) {
        if (item.isAvailable()) { ... }
      }
    }
  }
}

// Good — max 1 level per function
function process(order) {
  if (!order.isValid() || !order.hasItems()) return;
  order.items.filter(isAvailable).forEach(processItem);
}
```

**BLOCKING** when nesting exceeds 3 levels. **NON-BLOCKING** advisory at exactly 3.

## Dimension 2 — Linear Happy Path

The main success path must read top-to-bottom without branching. Errors and edge cases exit early via guard clauses, leaving the happy path unindented and unobstructed.

## Dimension 3 — Boolean Expression Complexity

**No compound boolean expression with more than 3 operands** joined by `&&` or `||` in a single expression. Extract complex boolean expressions into a named predicate function.

```
// Bad
if (user.age >= 18 && user.isVerified && !user.isBanned && user.subscription !== 'expired') {

// Good
if (isEligibleForAccess(user)) {
```

**BLOCKING** when more than 4 operands. **NON-BLOCKING** advisory at 3–4.

## Dimension 4 — Working Memory Load

Limit **simultaneous live, mutable local variables** in any single function to **5 or fewer**. A variable is live from declaration to last use. Beyond 5, working memory is saturated.

Immutable constants and single-use loop variables do not count.

## Dimension 5 — Function Self-Containment

Any function must be **fully understandable from its signature and body alone**. Temporal coupling — where A must be called before B, or B silently depends on prior state — is a cognitive load violation because the constraint is invisible at the call site.

**BLOCKING** when temporal coupling is present with no visible guard or assertion at the call site.

## Dimension 6 — Abstraction Consistency

All statements within a function body must operate at the **same level of abstraction**. Mixing high-level orchestration calls (`submitOrder`, `notifyCustomer`) with low-level mechanics (`db.execute("INSERT …")`) forces the reader to context-switch mid-read.

Flag only when the mixing is severe enough to materially degrade first-read comprehension.

## Dimension 7 — Surprise Factor

Code must do exactly what its name and visible signature imply — nothing more, nothing less. Hidden side effects, silent mutations, and counter-intuitive return values force the reader to mentally simulate execution.

**BLOCKING** — a function that does something other than what its name promises is always blocking.

## Dimension 8 — Visual Density

- **Line length:** 120 characters maximum.
- **Vertical spacing:** do not remove blank lines to compress code. Blank lines are paragraph breaks.
- **Chain length:** no method chain exceeding 4 calls on a single expression.

All visual density findings are **NON-BLOCKING** (advisory).

---

## Review cite format

`[READABILITY/<dimension>] <file>:<line or function> — <what was found and why it increases cognitive load>`

Example: `[READABILITY/NESTING] UserService.java:47 — 4-level nesting in processOrder(); extract inner loop to processAvailableItems()`

## Write-time checklist

1. No function body has more than 2 levels of nesting (3 is borderline; flag and refactor).
2. Happy path flows top-to-bottom without nested conditions.
3. No compound boolean expression has more than 3 operands.
4. No single function has more than 5 simultaneous live, mutable local variables.
5. Every function is fully understandable from its signature and body alone.
6. All statements within a function body operate at the same level of abstraction.
7. Every function does exactly what its name promises — no hidden effects.
8. No line exceeds 120 characters; logical blocks are separated by blank lines.
