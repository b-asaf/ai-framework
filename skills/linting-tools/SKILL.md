---
name: linting-tools
description: How to detect, run, and interpret linting and formatting tools. All tools run only if already configured in the project — never add or suggest a tool not already present. Loaded by the linter agent.
---

# Linting Tools

## Core rule
Run only what is already configured. Never install, suggest, or add a tool.

## Detection order
1. Scan for tool config files and dependencies
2. Report detected tools to orchestrator before running anything
3. If a tool is unreachable (SonarQube, Klocwork), report and skip — do not fail the pipeline

## Run order (all detected tools, in this sequence)
1. **Formatter** — Prettier / Biome format / ktlint format (fix style issues first)
2. **Linter** — ESLint / Biome lint / Checkstyle / PMD / ktlint check
3. **Static analysis** — SpotBugs / Detekt / Klocwork
4. **SonarQube** — if detected and reachable
5. **JFrog Xray** — always last (see `xray-scanning` skill)

## Auto-fix policy
Run auto-fix first. Report only violations that auto-fix cannot resolve — those route back to the implementation agent.

## References
- Frontend tool commands (Biome, ESLint, Prettier): read `references/frontend-tools.md`
- Backend tool commands (SonarQube, Checkstyle, SpotBugs, PMD, ktlint, Detekt, Klocwork): read `references/backend-tools.md`