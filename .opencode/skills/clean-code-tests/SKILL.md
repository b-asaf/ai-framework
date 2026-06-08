---
name: clean-code-tests
description: Use when writing, modifying, refactoring, or reviewing tests to enforce clean, reliable, single-behaviour test code following F.I.R.S.T. and TDD discipline.
---

# Clean Code — Tests

## F.I.R.S.T.

- **Fast.** Tests must run in milliseconds. Slow tests stop being run. If a test is slow, it is hitting real infrastructure — inject a test double instead.
- **Independent.** Tests must not depend on each other. Any test can run in any order, in isolation, and must produce the same result. Shared mutable state between tests is a violation.
- **Repeatable.** Tests produce identical results in any environment — dev machine, CI, any time of day. No reliance on real network, real filesystem, wall-clock time, or random values.
- **Self-validating.** A test passes or fails — no manual inspection of output or logs. Every test has an assertion.
- **Timely.** Tests are written before or alongside the code they cover, never weeks later.

## Test structure and clarity

- **One behaviour per test.** Each test verifies exactly one observable outcome. A failing test name alone must identify what broke.
- **No `should` prefix.** Name tests as statements of fact: `returnsUserForValidId`, `throwsWhenIdIsMissing`. Remove "should".
- **AAA — Arrange, Act, Assert.** One setup block, one action, one assertion block. Never interleave.
- **Short tests signal healthy design.** Aim for under 15 lines per test body. Long tests signal repeated setup (extract a factory/fixture) or multiple behaviours (split into focused tests).
- **Extract shared setup.** Repeated arrange code must be extracted into factory helpers or a `beforeEach` fixture. Test code follows the same DRY rule as production code.

## Test scope and integrity

- **Test observable outcomes, not implementation.** Assert on the public, visible result. Never assert on internal state, private methods, or the sequence of method calls. An equivalent refactor that produces the same output must not break any test.
- **Never test internals via mocks.** If you need a mock to assert that a private collaborator was called in a certain way, the production design likely needs refactoring.
- **Test code is production code.** Naming, functions, and comments rules apply equally to test files.
- **No magic values in tests.** Use named constants or descriptive builder parameters — `userId: KNOWN_ACTIVE_USER_ID` instead of bare `42`.

## Write-time checklist

Before committing any test:
1. Does the test name state a fact about behaviour without "should"?
2. Is there exactly one action and one assertion focus?
3. Is the test touching real network, filesystem, clock, or random values? Replace with test doubles.
4. Would a semantically equivalent refactor of the production code break this test? If yes, it is testing implementation — rewrite.
5. Does the arrange block exceed 5–8 lines? Extract a factory or fixture.

## Review cite format

`[TEST QUALITY] <test file>:<test name or line> — <rule violated and concrete improvement>`

Fragile tests (break on correct refactors), implementation-testing tests, and tests with no assertion are **BLOCKING** — they are worse than no tests. All other test quality issues are **NON-BLOCKING**.
