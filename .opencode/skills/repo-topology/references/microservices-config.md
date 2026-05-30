# Multi-Repo Microservices _opencode.json Templates

## Standard multi-repo (separate git repos per service)

```json
{
  "version": "1.0",
  "workspace": {
    "name": "[XXX]-Project",
    "is_multi_repo": true,
    "instructions": [
      "NEVER work directly on the 'main', 'master', 'develop' branch.",
      "For every task, create a feature branch in EACH repo that is touched.",
      "Agents may read git state but must never run git write commands.",
      "API contracts are defined before any implementation begins.",
      "PRs that span multiple services must be merged in dependency order."
    ]
  },
  "agents": {
    "manager": {
      "role": "product",
      "instructions": "Multiple git repos. Each touched repo needs its own branch. Contract-first for cross-service changes. Coordinate merge order."
    },
    "sub_agents": [
      {
        "name": "service-auth",
        "path": "./auth-service",
        "rules": "Auth service. Contract changes require api-gateway and all consumers to update. Never run git write commands."
      },
      {
        "name": "service-orders",
        "path": "./orders-service",
        "rules": "Orders service. Never run git write commands."
      },
      {
        "name": "service-payments",
        "path": "./payments-service",
        "rules": "Payments service. Never run git write commands."
      },
      {
        "name": "api-gateway",
        "path": "./api-gateway",
        "rules": "API gateway config only. Route changes must coordinate with affected services. Never run git write commands."
      },
      {
        "name": "frontend",
        "path": "./frontend",
        "rules": "Frontend. Consumes API contracts — update after contract PRs are merged. Never run git write commands."
      }
    ]
  }
}
```

## Hybrid (monorepo FE + separate BE services)

```json
{
  "version": "1.0",
  "workspace": {
    "name": "[XXX]-Project",
    "is_multi_repo": true,
    "instructions": [
      "NEVER work directly on the 'main', 'master', 'develop' branch.",
      "FE monorepo: one branch covers all FE package changes.",
      "Each BE service repo: separate branch per service touched.",
      "Agents may read git state but must never run git write commands.",
      "API contracts are defined before any implementation begins."
    ]
  },
  "agents": {
    "manager": {
      "role": "product",
      "instructions": "Hybrid topology: FE is a monorepo (one branch), each BE service is a separate repo (one branch per service). Contract-first for cross-service changes."
    },
    "sub_agents": [
      {
        "name": "service-be-1",
        "path": "./be-service-1",
        "rules": "Backend service. Never run git write commands."
      },
      {
        "name": "service-be-2",
        "path": "./be-service-2",
        "rules": "Backend service. Never run git write commands."
      },
      {
        "name": "frontend-app",
        "path": "./frontend/apps/web",
        "rules": "Frontend app in monorepo. Never run git write commands."
      },
      {
        "name": "frontend-shared",
        "path": "./frontend/libs/shared",
        "rules": "Shared FE library. Breaking changes require all FE consumers to update. Never run git write commands."
      }
    ]
  }
}
```

## Key multi-repo rules for all templates

- `"is_multi_repo": true` — each service repo needs its own branch
- The orchestrator tells the developer **which branch to create in which repo**:
  > "Please run `git checkout -b feat/add-payment-webhook` in `./payments-service`"
- Contract changes always sequence before implementation:
  1. API contract PR (merged first)
  2. Provider service PR (implements the contract)
  3. Consumer service PR (consumes the contract)
  4. Frontend PR (updates the API client)