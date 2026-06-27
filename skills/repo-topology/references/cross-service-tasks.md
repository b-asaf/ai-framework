# Cross-Service Task Sequencing

## When a task spans multiple services

The orchestrator must determine dependency order before routing to any implementation agent.

### Step 1 — Map the dependency graph

Ask: which services depend on changes in other services for this task?

```
Example: "Add payment webhook notification"
  payments-service  ← produces the webhook event
  notifications-service ← consumes it
  frontend ← displays notification status
  api-gateway ← may need a new route

Dependency order:
  1. payments-service (produces)
  2. notifications-service (consumes — needs payments contract first)
  3. api-gateway (routes — needs service contracts first)
  4. frontend (displays — needs API contract first)
```

### Step 2 — Contract first, always

If the task introduces a new API boundary between services:
1. Load the `api-contracts` skill
2. Define the contract (OpenAPI spec, GraphQL schema, message schema) **before any implementation**
3. Get developer approval on the contract
4. Only then route to implementation agents

### Step 3 — PR sequencing

Each service gets its own PR, merged in dependency order:

| PR | Service | Branch | Depends on |
|---|---|---|---|
| 1 | Contract definition | `feat/payment-webhook-contract` | — |
| 2 | payments-service | `feat/payment-webhook-producer` | PR 1 merged |
| 3 | notifications-service | `feat/payment-webhook-consumer` | PR 2 merged |
| 4 | api-gateway | `feat/payment-webhook-route` | PR 2 merged |
| 5 | frontend | `feat/payment-webhook-ui` | PR 3, PR 4 merged |

**Rule:** never merge a consumer PR before the provider PR. CI will catch it, but it wastes a pipeline run.

### Step 4 — Branch instructions per repo

For multi-repo projects, the orchestrator must tell the developer which branch to create in which repo:

```
For this task you need branches in 3 repos:

1. Please run in ./payments-service:
   git checkout -b feat/payment-webhook-producer

2. Please run in ./notifications-service:
   git checkout -b feat/payment-webhook-consumer

3. Please run in ./frontend:
   git checkout -b feat/payment-webhook-ui

Confirm all three branches are open before I start implementation.
```

For monorepos, one branch covers all changes:
```
This task touches 3 packages in the monorepo.
Please run in the repo root:
  git checkout -b feat/payment-webhook

All package changes go on this branch.
```

## Shared code changes (monorepo)

When the task requires a change to a shared library:

| PR | What | Rule |
|---|---|---|
| 1 | Shared lib change | Must be backwards compatible if possible |
| 2 | Consumer A update | After PR 1 merged |
| 3 | Consumer B update | After PR 1 merged |

If the shared lib change is breaking:
1. Add the new interface alongside the old (backwards compatible addition)
2. Update all consumers to use the new interface
3. Remove the old interface in a final cleanup PR

Never break all consumers in one PR. Never merge a consumer update before the shared lib PR.

## Testing cross-service changes locally

Before opening PRs, instruct the developer to verify locally:
- **Multi-repo:** run both services locally and test the integration manually or with contract tests
- **Monorepo:** run `nx affected --target=test` or equivalent workspace-aware test command from root
- **Always:** the contract (API spec, message schema) is the source of truth — both sides are tested against it