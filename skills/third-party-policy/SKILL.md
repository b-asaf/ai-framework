---
name: third-party-policy
description: Rules for handling 3rd party dependency changes. Any addition, removal, or version update requires explicit developer approval before being applied.
---

# Third-Party Dependency Policy

## The rule
**No dependency may be added, removed, or updated without explicit developer approval.**

This applies to:
- npm packages (`package.json`)
- Maven/Gradle artifacts (`pom.xml`, `build.gradle`)
- Python packages (`requirements.txt`, `pyproject.toml`)
- Any other package manager manifest

## How to request approval

When an agent determines a 3rd party change is needed, it must stop and output:

```
⚠️ Third-party approval required

Action: [ADD / REMOVE / UPDATE]
Package: [package name]
Version: [current version → proposed version] or [new: version]
Reason: [why this is needed for the current task]
Alternatives considered: [what was considered before this, or "none"]
Xray scan: [CLEAN / BLOCKERS FOUND / NOT RUN]
Security notes: [CVEs found by Xray or manual check, or "none found"]

Do you approve this change?
```

**Before requesting approval, always check for known vulnerabilities:**
- Run `jf audit` on the proposed package/version if Xray is configured
- If Xray is not configured, check the CVE databases manually (NVD, OSS Index)
- If any CVSS >= 8 vulnerability is found in the proposed version, do not request approval for that version — propose the next clean version instead
- If no clean version exists, flag this explicitly and present the developer with the options

Do not proceed until the developer explicitly confirms.

## Separate PR rule
A dependency change is always a separate PR from the feature that uses it:

1. PR 1 — `chore: add/update/remove [package]` — developer approves and merges first
2. PR 2 — `feat: [feature using the package]`

Never bundle a dependency change into a feature PR.

## For the code-reviewer and gatekeeper
Check the diff for changes to `package.json`, `pom.xml`, `build.gradle`, `requirements.txt`, or any lock file. If a dependency changed without documented approval, flag as a **blocker**.

## Automatic flags
The following always trigger a mandatory approval stop — no exceptions:
- Any package with a CVSS >= 8 vulnerability in the proposed version — propose a clean version instead
- Any package where no clean version exists — present developer with options before proceeding
- Any package that changes the build output significantly (bundler, compiler, transpiler)
- Any package that adds a new external network dependency at runtime
- Any package not actively maintained (last commit > 2 years, no recent releases)