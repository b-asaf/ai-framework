---
name: xray-scanning
description: JFrog Xray security scanning rules. Detects, runs, and interprets Xray vulnerability scans on dependencies and build artifacts. Any issue with CVSS score >= 8 is a hard blocker — the PR cannot proceed until resolved. Loaded by the linter agent.
---

# JFrog Xray Scanning

## What Xray scans

JFrog Xray performs deep recursive scanning of:
- **Dependencies** — every transitive dependency in the dependency graph
- **Build artifacts** — JARs, Docker images, npm packages produced by the build
- **Licenses** — flags policy violations (loaded separately if license policy is configured)

Xray uses **CVSS (Common Vulnerability Scoring System)** to score vulnerabilities:

| CVSS Score | Severity | Action |
|---|---|---|
| 9.0 – 10.0 | Critical | **Hard blocker — must fix before PR** |
| 8.0 – 8.9 | High | **Hard blocker — must fix before PR** |
| 4.0 – 7.9 | Medium | Warning — flag to developer, no block |
| 0.1 – 3.9 | Low | Informational — report only |

**Score >= 8 is a hard blocker. The PR cannot be handed off to the developer until all such issues are resolved.**

---

## Detection

Xray is active if any of the following are found:

| Signal | Location |
|---|---|
| `xray` section in `.jfrog/projects/*.yaml` | Project config |
| `jf` CLI available and authenticated | `jf --version` |
| `JFROG_URL` or `JFROG_ACCESS_TOKEN` env vars | Environment |
| Xray scan step in CI pipeline | `azure-pipelines.yml`, `.github/workflows/`, `Jenkinsfile` |
| `jfrog-plugin` in Maven/Gradle config | `pom.xml`, `build.gradle` |

If Xray is not detected, report this to the orchestrator and skip — do not fail the pipeline for a missing tool.

---

## How to run

### Using JFrog CLI (`jf`)

```bash
# Scan the current project directory
jf audit

# Scan with specific package manager
jf audit --mvn         # Maven
jf audit --gradle      # Gradle
jf audit --npm         # npm
jf audit --yarn        # Yarn
jf audit --pip         # Python

# Output as JSON for structured parsing
jf audit --format json

# Scan a specific build artifact
jf scan path/to/artifact.jar
jf scan path/to/image.tar
```

### Using Maven plugin

```bash
./mvnw jfrog:audit
```

### Using CI-triggered scan
If the project relies on CI to run Xray (scan triggered on artifact publish), report this to the orchestrator — the scan result must be retrieved from the JFrog platform before gating.

---

## Interpreting results

### JSON output structure
```json
{
  "vulnerabilities": [
    {
      "cves": [{ "id": "CVE-2024-XXXX", "cvssV3Score": 9.1 }],
      "severity": "Critical",
      "components": [{ "name": "org.example:library", "version": "1.2.3" }],
      "fixedVersions": ["1.2.4", "2.0.0"],
      "summary": "Remote code execution via..."
    }
  ]
}
```

### Triage logic

For each vulnerability found:

1. Extract CVSS score and severity
2. If score >= 8:
   - Mark as **BLOCKER**
   - Identify the affected component and version
   - Check `fixedVersions` — if a fix exists, propose the upgrade
   - If no fix exists, flag for developer decision (remove dependency / isolate / accept risk with justification)
3. If score < 8:
   - Mark as **WARNING**
   - Include in report but do not block

---

## Remediation paths

When a blocker is found, the linter agent must propose one of:

| Path | When to use |
|---|---|
| **Upgrade** | A fixed version exists — propose a `chore:` PR to upgrade |
| **Replace** | No fix available — propose an alternative dependency |
| **Remove** | Dependency is unused or can be removed entirely |
| **Isolate** | Dependency cannot be changed — propose sandboxing or input validation workaround |
| **Developer decision** | None of the above apply — present the CVE details and wait for explicit developer instruction |

All remediation paths that involve dependency changes follow the `third-party-policy` skill — a separate `chore:` PR, developer-approved, before the feature PR continues.

---

## Output format (appended to Lint Report)

```
## Xray Security Scan

### Status: PASS / FAIL (blockers found) / SKIPPED (not configured)

### Tools run
- jf audit [version] — [scope: npm / mvn / gradle / etc.]

### Blockers (CVSS >= 8) — PR cannot proceed
| CVE | Score | Severity | Component | Fixed In | Proposed action |
|---|---|---|---|---|---|
| CVE-2024-XXXX | 9.1 | Critical | org.example:lib:1.2.3 | 1.2.4 | Upgrade to 1.2.4 (separate chore: PR) |

### Warnings (CVSS < 8) — informational
| CVE | Score | Severity | Component | Notes |
|---|---|---|---|---|
| CVE-2024-YYYY | 5.3 | Medium | some-package:2.1.0 | No fix available |

### Required actions
- Developer must approve upgrade of [component] to [version] before this PR can proceed
```

---

## Scope creep prevention

Xray findings are reported per PR, not for the entire codebase. Only flag vulnerabilities introduced or exposed by the **current PR's dependency changes**. Do not re-raise pre-existing issues that are not touched by this PR — those belong in a separate `chore:` PR tracked independently.