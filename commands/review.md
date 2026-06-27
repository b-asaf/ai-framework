---
description: Run the full post-implementation review pipeline on the current branch — linter, code-reviewer, qa, gatekeeper.
---

Run the post-implementation pipeline on the current branch:

1. Load `static-code-analysis` skill — run lizard + jscpd on changed files.
2. Route to `@linter` — run all detected linting tools.
3. Route to `@code-reviewer` — full review with BLOCKING/NON-BLOCKING classification.
4. Route to `@qa` — verify test coverage on changed lines, write missing tests.
5. Route to `@gatekeeper` — validate all acceptance criteria, persist any new patterns.

Report the final verdict: PASS or FAIL with the list of blocking issues.
