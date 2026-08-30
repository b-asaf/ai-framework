# Decision: Correct the mutation testing gate mechanism with real smoke-test evidence

**Date:** 2026-08-19
**Status:** accepted

## Context
`DEC-006` designed the mutation testing gate around computing a mutation score by counting
statuses in Stryker's JSON output. A real smoke test (scratch TS project, Stryker,
deliberately under-tested function) found something better, not just confirmation:

1. **Real environment bug, unrelated to design**: `npx stryker run` failed with `TypeError:
   ts.parseConfigFileTextToJson is not a function` — a very recent TypeScript release
   removed a deprecated internal API Stryker's `TSConfigPreprocessor` still depends on.
   Confirmed fix: pin `typescript@5.x` rather than letting `npm install` grab the newest
   release (Stryker's own typescript-checker only requires `>=3.6`).
2. **A cleaner mechanism than designed**: Stryker's `stryker.conf.json` supports a
   `thresholds.break` value, and Stryker sets its own process exit code based on it —
   confirmed directly: `ERROR MutationTestReportHelper Final mutation score 80.00 under
   breaking threshold 90, setting exit code to 1 (failure)`. Pass/fail should be determined
   by Stryker's exit code, matching the "prefer exit code" pattern already used for adapter
   commands and the OpenCode engine contract elsewhere in this framework's history — not by
   a custom score computation over the JSON report.
3. The real JSON shape was also confirmed (no top-level score field; per-mutant `status`,
   `mutatorName`, `location.start.line`) — still needed, but only for the detailed
   survived-mutant breakdown after a failure, not for the pass/fail decision itself.

## Decision
`skills/mutation-testing/SKILL.md` corrected: `stryker.conf.json` now sets
`thresholds.break` to the configured threshold; the gate checks Stryker's exit code first,
and only parses the JSON report when the exit code indicates failure, to build the specific
rejection message. Prerequisites section gains the TypeScript version-pinning requirement.

## Reasoning
1. Agent or deterministic? Both the original and corrected design were deterministic — this
   is a correction to *which* deterministic signal is authoritative (tool-native exit code
   vs. custom computation), not a change in kind.
2. Trade-off: none — the corrected approach is strictly simpler and more reliable than
   reimplementing Stryker's own threshold logic.
3. Cheaper alternative: this correction IS the cheaper alternative to the original design.
4. Visibility gained: none of this changes what a developer sees in the rejection message —
   it only makes the underlying check more accurate to how Stryker actually works.

## Consequences
- Any project's `stryker.conf.json` written before this correction should be checked for a
  `thresholds.break` value matching its configured `mutationTesting.threshold`.
- PIT's equivalent exit-code/threshold behavior remains unverified — flagged explicitly in
  the skill rather than assumed symmetric with Stryker's confirmed behavior.
- This is a direct example of why smoke-testing before finalizing a skill matters even for
  seemingly well-documented third-party tools — the better mechanism (`thresholds.break`)
  was only discovered by running the real tool, not by reading its docs in advance.
