---
name: project-overview
description: Project-specific context. Populated automatically on first run by scanning the codebase. Every agent loads this first. If it contains [XXX] or is empty, trigger first-run analysis before proceeding.
---

# Project Overview

> **Status:** [UNPOPULATED — first-run analysis required]
> When an agent detects this status, it must perform a full codebase scan and populate this file before doing anything else. Confirm findings with the developer before proceeding.

---

## Project name
[XXX]

## Architecture topology
- Type: [Monolith / Microservices / Hybrid] — confirmed by developer on [date]
- Services: [list of services with paths, or "single BE + single FE"]
- API gateway: [yes — path / no]
- Shared libraries: [yes — path / no]
- Containerization: [Docker / Kubernetes / none]

## Workspace layout
```
[XXX]/
├── [XXX]-be/    # [language] [framework] backend
└── [XXX]-fe/    # [framework] frontend
```

## Repo state
- [XXX]-be: [new / partial / mature] — [N source files, M tests, CI: yes/no]
- [XXX]-fe: [new / partial / mature] — [N source files, M tests, CI: yes/no]

## Backend stack
- **Language:** [detected]
- **Framework:** [detected]
- **Build tool:** [detected]
- **Test framework:** [detected]
- **Linter/static analysis:** [detected]
- **Database:** [detected or "none — in-memory"]
- **Migration tool:** [detected or "none"]
- **API style:** [REST / GraphQL / gRPC / detected]
- **Key dependencies:** [detected]
- **Local dev command:** [detected]
- **Build/test command:** [detected]
- **Critical gotchas:** [discovered from codebase]

## Frontend stack
- **Language:** [detected]
- **Framework:** [detected]
- **Build tool:** [detected]
- **State management:** [detected]
- **API client:** [detected]
- **UI/component library:** [detected or "none"]
- **Styling approach:** [detected]
- **Test framework:** [detected]
- **Linter/formatter:** [detected]
- **Key dependencies:** [detected]
- **Local dev command:** [detected]
- **Build/test command:** [detected]
- **Critical gotchas:** [discovered from codebase]

## Layer architecture
[Discovered from codebase — e.g. controller → service → repository]

## Existing patterns & conventions
[Discovered from codebase — naming, file structure, import style, etc.]

## Discovered patterns

> This registry is updated incrementally by agents whenever a new domain is encountered. It is the single source of truth for pattern enforcement across all agents. See the `pattern-enforcement` skill for how entries are added and what each status means.

| Domain | Pattern | Example | Status |
|---|---|---|---|
| [populated by agents during discovery] | | | |

## CI/CD setup
[Detected from .github/, azure-pipelines.yml, Jenkinsfile, etc. or "none detected"]

## Git hooks
- [XXX]-be: [husky / lefthook / plain scripts / not installed]
- [XXX]-fe: [husky / lefthook / plain scripts / not installed]
- Protected branches: main, master, develop
- Commit format: conventional commits

## Localization
- Library: [react-i18next / react-intl / lingui / custom / none]
- Default language: en
- Active languages: [en, he, ...] or [none detected]
- RTL support: [implemented / partial / not implemented]
- Translation file location: [src/i18n/locales/ or custom path]
- Android strings: [values/ + values-he/ etc. or not found]
- Shared string sync: [manual / script / not set up]
- Gaps: [any missing locales, unsynced strings, missing RTL handling]

## 3rd party integrations
[Detected external services, APIs, or SDKs]

## Project documentation location
[e.g. docs/, README.md, wiki]