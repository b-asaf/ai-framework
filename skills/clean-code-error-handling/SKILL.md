---
name: clean-code-error-handling
description: Use when writing, modifying, refactoring, or reviewing error paths, exceptions, null handling, and failure boundaries to keep error handling robust and readable.
---

# Clean Code — Error Handling

## Rules

- **Use exceptions, not error codes.** Returning error codes forces every caller to check the return value inline. Throw typed, named exceptions instead.
- **Write the try/catch first.** Start error-handling code with the `try` block. Define what can succeed and what is thrown before filling in the happy path.
- **Extract try/catch bodies.** The body inside `try` and the body inside `catch` should each be a single delegating call to an extracted function. Error handling is its own responsibility; do not mix it with logic.
- **Define exceptions in terms of the caller's needs.** Wrap third-party exceptions at the boundary so domain code never sees vendor-specific exception types (`SQLException`, `AxiosError`, etc.).
- **Never return null to signal failure.** Throw an exception if the case is erroneous, or return a Null Object / empty collection if absence is normal.
- **Never pass null as an argument** in business logic. Use `Optional` types or overloaded functions.
- **Provide context in exceptions.** Include enough information in the message to understand what was being attempted and why it failed.
- **Never swallow exceptions.** `catch (Exception e) {}` hides failures silently. Either handle meaningfully or rethrow.

## Write-time checklist

Before committing any error-handling code:
1. Am I communicating failure via exception or via return value? Switch to exception.
2. Is my try block body a single call to an extracted function?
3. Could the caller receive `null` from this function? Throw or return a Null Object instead.
4. Am I exposing a third-party exception type across a boundary? Wrap it.
5. Does my exception message tell a new developer what went wrong and where?

## Review cite format

`[ERROR HANDLING] <file>:<line or function name> — <rule violated and concrete improvement>`

All error handling violations are **BLOCKING** — swallowed exceptions, null returns on failure, and exposed vendor exception types cause silent production failures.
