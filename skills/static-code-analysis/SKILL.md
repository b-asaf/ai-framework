---
name: static-code-analysis
description: Run a static code analysis gate using lizard (cyclomatic complexity) and jscpd (duplication) on changed files. Used by linter agent as a pre-review gate and by code-reviewer as a precheck before reading any code.
---

# Static Code Analysis

## Purpose

Run a lightweight, objective quality gate on changed files before human review begins. Enforces cyclomatic complexity and duplication thresholds. Scoped to the current change set — legacy violations outside the diff are recorded as context, not blocking.

---

## Thresholds (authoritative — do not restate elsewhere)

| Metric | Threshold |
|---|---|
| Cyclomatic complexity per function | max `10` |
| Duplication in changed lines | max `10%` |
| Changed-line test coverage | min `90%` |

---

## Prerequisites

Install once, globally:

```bash
pip install lizard
npm install -g jscpd
```

If either tool is missing when the command runs, **stop immediately** and report:

```
STATIC ANALYSIS — ENVIRONMENT PREREQUISITE FAILURE
Missing: [lizard | jscpd]
Install with: [pip install lizard | npm install -g jscpd]
Do not proceed until the tool is installed.
```

Do not treat a missing tool as a code failure. It is an environment issue the developer must resolve.

---

## How to run

**Cyclomatic complexity (lizard):**

```bash
lizard --warnings_only --CCN 10 <file-or-dir> [...]
```

**Duplication (jscpd):**

```bash
jscpd --threshold 10 --reporters json --output .jscpd-report <file-or-dir> [...]
# or without global install:
npx jscpd --threshold 10 --reporters json --output .jscpd-report <file-or-dir> [...]
```

Examples:

```bash
# Single file
lizard --warnings_only --CCN 10 src/UserService.java

# Directory
jscpd --threshold 10 --reporters json --output .jscpd-report src/
```

---

## Scope policy

Run whole-file tools, but enforce thresholds only for findings that intersect the **current change set** (the diff).

- **Complexity fails** only when an over-threshold function was introduced or modified by the current diff.
- **Duplication fails** only when duplicated blocks intersect changed lines and the duplication was introduced by the current change.
- **Coverage fails** only when changed-line coverage is at or below the configured minimum.
- Existing legacy violations outside changed lines → **record as context**, not blockers. Do not expand task scope.

---

## Gate semantics

| Outcome | Result |
|---|---|
| Tool missing | PREREQUISITE FAILURE — stop, report install command |
| Threshold failure in current diff | BLOCKING — reject before reading any code |
| Threshold failure outside current diff | NON-BLOCKING — record as legacy context |
| Coverage infrastructure missing | Record as unavailable, continue |
| Coverage below threshold on changed lines | BLOCKING |
| All checks pass | Proceed to code review |

---

## Usage by agent

**`@linter`:** Runs static analysis as step 3 in the run order (after formatter and linter, before SonarQube and Xray). Reports results in the lint report.

**`@code-reviewer`:** Runs static analysis as a **precheck before reading any code**. If static analysis fails or cannot run on the changed paths, issue an immediate rejection without reading the implementation. Do not inspect implementation details until this check passes.

```
REVIEW — REJECTED
[STATIC ANALYSIS] Static analysis failed or could not run — review stopped before reading code
```

**Coverage precheck:** After static analysis passes, check changed-line coverage if the repo has coverage infrastructure wired. If coverage is below the threshold defined in this skill, reject immediately.

```
REVIEW — REJECTED
[COVERAGE] Changed-line coverage below 90% — review stopped before reading code
```
