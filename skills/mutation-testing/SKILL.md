---
name: mutation-testing
description: Injects deliberate bugs (mutants) into changed code and confirms the test suite catches them. An objective signal that tests assert real behavior, not just execute lines. Optional/configurable — scoped to the highest-CRAP-score changed functions by default to keep it fast, not the whole diff.
---

## Quick reference

- **Tools:** Stryker (JS/TS, `stryker.conf.json`/`.js`) · PIT (Java, via `pitest-maven`/pitest Gradle plugin — declared in `pom.xml`/`build.gradle`)
- **Trigger:** optional, configured per project (same as `qualityscan`/Xray in `static-code-analysis` — absence is a skip, not a failure)
- **Scope by default:** only changed functions with a CRAP score above the project's threshold (`crap-score` skill) — not the full diff. This is what keeps it fast enough to actually run.
- **Metric:** mutation score, gated via Stryker's own `thresholds.break` config — **confirmed
  by direct testing that Stryker sets its own process exit code based on this** (exit 0 =
  pass, exit 1 = below threshold). No custom score computation needed for pass/fail; the
  JSON report is only parsed for the detailed survived-mutant breakdown after a failure.
- **On breach:** report survival details (which mutants survived, what assertion would have
  caught them — real field names: `status`, `mutatorName`, `location.start.line`); ask the
  developer, same waiver pattern as Stage 1–3 — never auto-write a stronger test.

## Purpose

Coverage and CRAP score both measure whether code is *executed* by tests. Neither measures whether the assertions would actually catch a real bug. Mutation testing answers that directly: inject a small, deliberate defect (flip a comparison operator, remove a null check, change a return value) and confirm the suite fails. A mutant that survives means the line is executed but not actually verified.

Verified directly (not assumed): a function with an untested branch (`if (isMember) {...} return price;`, tested only for `isMember: true`) produced exactly one surviving mutant — the one that collapsed the untested branch's condition — while every mutant on the tested branch was killed. The concept works as designed.

---

## Prerequisites

**JS/TS:** Stryker installed and configured (`stryker.conf.json` present, `jsonReporter.fileName` set — see "How to run" below). **Also requires pinning TypeScript to a version Stryker's preprocessor actually supports** — a very recent TypeScript release removed the deprecated `ts.parseConfigFileTextToJson` API Stryker's `TSConfigPreprocessor` still depends on, causing `TypeError: ts.parseConfigFileTextToJson is not a function`. Fix confirmed: pin `typescript@5.x` (Stryker's own typescript-checker only requires `>=3.6`) rather than letting `npm install` grab the newest release.
**Java (Maven):** `pitest-maven` plugin declared in `pom.xml`.
**Java (Gradle):** pitest Gradle plugin declared in `build.gradle`/`build.gradle.kts`.

If none of these are present, this gate is skipped and reported as "not configured" — never run with an assumed default tool.

---

## Configuration

```json
{
  "mutationTesting": {
    "threshold": 70,
    "scope": "crap-flagged"
  }
}
```

- `threshold` — minimum acceptable mutation score (%). No built-in default; a project with no configured threshold skips this gate.
- `scope` — `"crap-flagged"` (default: only functions the `crap-score` gate flagged, or that exceed the same threshold, if `crap-score` itself isn't configured) or `"full-diff"` (every changed function — slower, opt in explicitly if wanted).

---

## How to run

**JS/TS (Stryker), scoped** — via config file, using Stryker's own built-in break
threshold, not custom score computation. Confirmed directly: Stryker sets its own process
exit code based on this — `ERROR MutationTestReportHelper Final mutation score 80.00 under
breaking threshold 90, setting exit code to 1 (failure)`.

`stryker.conf.json`:
```json
{
  "testRunner": "vitest",
  "mutate": ["<crap-flagged file globs>"],
  "reporters": ["json"],
  "jsonReporter": { "fileName": ".agentflow/mutation-result.json" },
  "thresholds": { "high": 80, "low": 60, "break": <configured threshold> }
}
```
```bash
npx stryker run
```
Exit code 0 = at/above threshold, no gate action needed. Exit code non-zero = below
threshold — the JSON report is then read, but only for the detailed "which mutant survived"
breakdown in the rejection message, not for the pass/fail decision itself, which the exit
code already gives you directly.

**Java Maven (PIT), scoped:**
```bash
mvn -B org.pitest:pitest-maven:mutationCoverage -DtargetClasses=<crap-flagged classes>
```

**Java Gradle (PIT), scoped:**
```bash
./gradlew pitest -PtargetClasses=<crap-flagged classes>
```

PIT's own exit-code/threshold behavior has not been directly verified the way Stryker's was
above — confirm before assuming symmetry between the two tools.

When `scope` is `"full-diff"`, omit the class/file scoping arguments and run against every changed file instead.

### Parsing the JSON output (Stryker) — for the rejection message only, not pass/fail

```json
{
  "files": {
    "<path>": {
      "mutants": [
        {
          "id": "1",
          "mutatorName": "ConditionalExpression",
          "replacement": "true",
          "status": "Survived",
          "location": { "start": { "line": 2, "column": 7 }, "end": { "line": 2, "column": 15 } }
        }
      ]
    }
  }
}
```

For each `"Survived"` mutant, `mutatorName` + `location.start.line` gives exactly what's
needed for the rejection message — read only when the exit code already signaled failure.

---

## Scope policy

Same discipline as `static-code-analysis` and `crap-score`:
- Only changed functions are in scope — pre-existing low-mutation-score code outside the diff is legacy context, not a blocker.
- Default scope is further narrowed to CRAP-flagged functions specifically, to keep this gate affordable to run on every review rather than only occasionally.

---

## Gate semantics

| Outcome | Result |
|---|---|
| No `mutationTesting` threshold configured | SKIPPED — reported as not configured |
| Tool not detected (no Stryker/pitest config) | SKIPPED — reported as unavailable |
| Tool exits 0 (score at/above threshold) | PASS |
| Tool exits non-zero (score below threshold) | ASK — parse the JSON report for the specific survived mutant(s) (file/line/mutator), report to the developer; they choose to strengthen the test (triggers scoped rework, then re-run this gate) or accept and proceed |

Never silently pass a breach. Never auto-write assertions without the developer choosing to.