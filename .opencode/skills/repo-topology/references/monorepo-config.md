# Monorepo _opencode.json Templates

## Nx / Turborepo / pnpm workspaces

```json
{
  "version": "1.0",
  "workspace": {
    "name": "[XXX]-Project",
    "is_multi_repo": false,
    "instructions": [
      "NEVER work directly on the 'main', 'master', 'develop' branch.",
      "For every task, create a new feature branch with the correct prefix.",
      "Agents may read git state but must never run git write commands.",
      "Shared packages in libs/ or packages/shared/ require all consumers to be updated."
    ]
  },
  "agents": {
    "manager": {
      "role": "product",
      "instructions": "Coordinate agents. One git repo — branch once, all changes on that branch. Shared lib changes always go first."
    },
    "sub_agents": [
      {
        "name": "backend",
        "path": "./apps/api",
        "rules": "Backend app. Never run git write commands. Check libs/ for shared code before creating new utilities."
      },
      {
        "name": "frontend",
        "path": "./apps/web",
        "rules": "Frontend app. Never run git write commands."
      },
      {
        "name": "shared-lib",
        "path": "./libs/shared",
        "rules": "Shared library. Breaking changes require ALL consumers to be updated in the same PR sequence. Never run git write commands."
      },
      {
        "name": "ui-lib",
        "path": "./libs/ui",
        "rules": "Shared UI component library. Breaking changes require ALL consumers to be updated. Never run git write commands."
      }
    ]
  }
}
```

## Maven multi-module

```json
{
  "version": "1.0",
  "workspace": {
    "name": "[XXX]-Project",
    "is_multi_repo": false,
    "instructions": [
      "NEVER work directly on the 'main', 'master', 'develop' branch.",
      "For every task, create a new feature branch with the correct prefix.",
      "Agents may read git state but must never run git write commands.",
      "Build from the root pom.xml — never from a module directly unless testing that module only."
    ]
  },
  "agents": {
    "manager": {
      "role": "product",
      "instructions": "One git repo, multiple Maven modules. Coordinate agents. Root build validates all modules."
    },
    "sub_agents": [
      {
        "name": "api-module",
        "path": "./api",
        "rules": "API module. Never run git write commands."
      },
      {
        "name": "domain-module",
        "path": "./domain",
        "rules": "Domain/core module. Changes here affect all other modules. Never run git write commands."
      },
      {
        "name": "infra-module",
        "path": "./infrastructure",
        "rules": "Infrastructure module. Never run git write commands."
      },
      {
        "name": "frontend",
        "path": "./frontend",
        "rules": "Frontend module. Never run git write commands."
      }
    ]
  }
}
```

## Key monorepo rules for all templates

- `"is_multi_repo": false` — one git repo means one branch for the whole task
- The orchestrator instructs git operations once — not once per package
- Build validation runs from the workspace root (Nx, Turborepo, or root `pom.xml`)
- Shared package paths appear as `shared-lib` sub_agents — changes there always sequence first