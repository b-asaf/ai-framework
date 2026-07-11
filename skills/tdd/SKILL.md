---
name: tdd
description: Use when writing code for a new feature or bug fix. Enforces the Iron Law — no production code without a failing test first. Red-green-refactor discipline, vertical slices, tests as the design tool.
---

## Quick reference

**The Iron Law:** No production code without a failing test first. No exceptions.

**Cycle:** RED (write failing test) → GREEN (minimum code to pass) → CHECK (full suite) → REFACTOR (clean up) → REPEAT

**Good test:** one behaviour, fast, isolated, no network/db/filesystem, AAA structure, named after behaviour not implementation.

**Bad test:** tests implementation details, multiple assertions on different behaviours, skipped red phase.

**Vertical slices:** thinnest end-to-end path first. Don't build entire layers — build one thin slice completely.

# Test-Driven Development

## The Iron Law

**No production code without a failing test first.**

Write code before the test? Delete it. Start over. No exceptions. No "I'll add tests after". No "this part is too simple to test". The law applies to every line.

Violating the letter of the rule is violating the spirit of the rule. This cuts off all "I'm following the spirit" rationalisations.

---

## The cycle

```
RED   → Write the smallest test that fails for the right reason
GREEN → Write the minimum production code to make it pass
        (ugly is fine — make it work first)
CHECK → Run the full suite. All tests must pass, not just the new one.
REFACTOR → Clean up. Extract duplication. Improve names.
            Tests must still pass after every refactor step.
REPEAT
```

Never skip the RED phase. A test that passes before you write production code is not a test — it's a lie. Verify the test fails, and verify it fails **for the right reason** (the behaviour you're about to implement is missing, not a compile error or wrong assertion).

---

## Completion criterion

Each TDD cycle is complete when:
- The failing test exists and describes one specific behaviour
- The minimum production code makes it pass
- The full suite passes (no regressions introduced)
- The code is refactored clean (no duplication, names reveal intent)

The task is complete when all acceptance criteria have a passing test and the suite is green.

## Vertical slices

Work one vertical slice at a time. A vertical slice is the thinnest end-to-end path through the feature — from the outermost interface to the innermost implementation — that delivers observable value.

Don't build the entire data layer, then the service layer, then the controller. Build one complete thin slice: a single endpoint that does one thing, tested end-to-end, before adding the next slice.

**Why:** Vertical slices keep each TDD cycle short and independently verifiable. They also prevent the common failure mode of building a complete implementation that turns out to solve the wrong problem.

---

## What makes a good test

### Tests must be:
- **Specific** — one test, one behaviour. If the name needs "and", split it.
- **Fast** — no network, no filesystem, no database in unit tests. Mock them.
- **Isolated** — tests must not depend on each other. Run in any order.
- **Readable** — the test is documentation. Name it after the behaviour, not the implementation.
- **Trustworthy** — a failing test means the behaviour is broken. Always. No flakiness tolerated.

### Test naming
Describe behaviour, not implementation:
```
✅ shouldReturnEmptyListWhenNoUsersExist
✅ givenExpiredToken_whenRefreshing_thenReturnsNewToken
❌ testUserService
❌ test1
```

### Given / When / Then structure
Every test has three sections, always in this order:
```
// Given — set up the world
// When  — perform the action
// Then  — assert the outcome
```

---

## What makes a bad test

**Testing implementation details** — if refactoring breaks your tests without changing behaviour, the tests are wrong. Test what the code does, not how.

**Mocking what you own** — mock external dependencies (HTTP, DB, filesystem). Don't mock your own classes to test other classes.

**Testing multiple behaviours** — one assertion per test, or at most assertions about the same behaviour. Separate concerns into separate tests.

**Skipping the red phase** — a green test you didn't see fail first tells you nothing.

**Snapshot tests as a substitute for assertions** — snapshots catch regressions but don't describe intent. Always prefer explicit assertions.

---

## Mocking rules

Mock at the boundary between your code and the outside world:
- HTTP clients
- Database connections
- File system
- External SDKs
- Clock / time

Do **not** mock:
- Your own services (test them directly or through integration tests)
- Pure functions
- Value objects

In the test, the mock is the specification. If your mock is complex, that's a signal your interface is complex.

---

## Refactoring rules

Refactor only when tests are green. Never refactor and add behaviour in the same step.

Safe refactors (tests must still pass):
- Rename a variable, method, or class
- Extract a method or class
- Inline a variable
- Move code to a better location
- Remove duplication

Unsafe in the refactor phase (stop, write a test first):
- Changing behaviour
- Adding a new path through the code
- Changing an interface

---

## When to stop

The cycle is complete when:
1. All acceptance criteria from the spec are covered by passing tests
2. The full test suite passes
3. No test is testing implementation details
4. The code has been refactored — no duplication, clear names, single responsibility

Do not declare done until all four are true.