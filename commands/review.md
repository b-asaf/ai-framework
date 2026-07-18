---
description: Run the full post-implementation review pipeline on the current branch — code-reviewer (lint+scan+review), qa, gatekeeper.
---

Run the post-implementation pipeline on the current branch:

1. Load `static-code-analysis` skill — run lizard + jscpd on changed files.
2. Route to `@code-reviewer` — lint/security scan, then full review with BLOCKING/NON-BLOCKING classification, in one pass.
3. Route to `@qa` — verify test coverage on changed lines, write missing tests.
4. Route to `@gatekeeper` — validate all acceptance criteria, persist any new patterns.

Report the final verdict: PASS or FAIL with the list of blocking issues.
