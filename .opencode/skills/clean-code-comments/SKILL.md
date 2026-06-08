---
name: clean-code-comments
description: Use when writing, modifying, refactoring, or reviewing code comments to decide when a comment is justified and when naming or structure should replace it.
---

# Clean Code — Comments

## Rules

- **A comment is an admission of failure.** Every comment acknowledges that you could not express intent through naming or structure. Before writing a comment, try harder to rename or restructure.
- **Comments lie.** Code changes; comments do not keep up. A misleading comment is worse than no comment.
- **Never describe what the code does.** `// increment i` above `i++` is pure noise.
- **Never use journal comments.** Source control is the changelog. `// Added 2024-03-01: fixed null check` is clutter.
- **Never leave commented-out code.** Delete it. It lives in git history.
- **Never use closing-brace comments.** `} // end if`. If you need them, your function is too long.
- **Never use noise comments.** `// Constructor`, `// Returns the day of the month` — these say nothing.
- **No position markers / banner comments.** `///// ---- Section A ---- /////` is a sign of a class that is too large and needs to be split.

**Acceptable comments (rare):**
- Legal/license headers at the top of a file
- Explanation of a non-obvious *external* constraint (e.g. a workaround for a documented third-party bug, with a link to the issue)
- Public API documentation where a contract is not self-evident from types and names alone
- `TODO` markers that are tracked and have an owner

## Write-time checklist

Every time you reach for a comment, stop and ask:
1. Can I rename the variable, function, or class to make this obvious?
2. Can I extract a function with a descriptive name that replaces this comment?
3. Is this truly a rare case where an external constraint cannot be expressed in code?

If (1) or (2) is possible, do it instead. Only write a comment if (3) is true.

## Review cite format

`[COMMENTS] <file>:<line> — <type of comment violation and what should replace it>`

Commented-out code is **BLOCKING**. All other comment violations are **NON-BLOCKING**.
