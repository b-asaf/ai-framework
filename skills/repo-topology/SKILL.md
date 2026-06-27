---
name: repo-topology
description: Detects and handles the workspace topology — single repo, monorepo, multi-repo microservices, or hybrid. Defines routing rules, shared code ownership, and cross-service task sequencing. Loaded by first-run-analysis, orchestrator, and architect.
---

# Repo Topology

## Step 1 — Detect topology

Scan the workspace root. Look for:

**Monorepo signals** (single git repo, multiple packages):
- `nx.json` or `nx` in `package.json` devDependencies → Nx monorepo
- `turbo.json` or `turbo` in `package.json` → Turborepo
- `pnpm-workspace.yaml` → pnpm workspaces
- `packages/`, `apps/`, `libs/` directories at root
- Maven multi-module: multiple `pom.xml` at different levels under one `.git`
- Gradle multi-project: `settings.gradle` with `include` directives

**Multi-repo microservices signals**:
- Multiple sibling folders each with their own `.git`
- `docker-compose.yml` referencing multiple app services
- Kubernetes manifests across folders
- API gateway config (Kong, Nginx, Traefik)

**Single repo signals**:
- One `.git` at workspace root
- One `pom.xml` / `package.json` / `pyproject.toml` at repo root
- No workspace manager config

## Step 2 — Confirm with developer

Always ask — never assume:
```
🔍 Topology detected: [Monorepo / Multi-repo microservices / Single repo / Unclear]
Signals: [list what was found]

Which best describes this project?
1. Single repo (one BE + one FE, separate git repos)
2. Monorepo (multiple packages in one git repo)
3. Multi-repo microservices (multiple BE services, separate git repos)
4. Hybrid (e.g. monorepo FE + separate BE services)
```

## Step 3 — Apply topology rules

For `_opencode.json` templates: read `references/monorepo-config.md` or `references/microservices-config.md`

### Single repo (default)
No changes needed. Standard `_opencode.json` applies.

### Monorepo
- Detect workspace manager (Nx, Turborepo, pnpm, Maven multi-module, Gradle multi-project)
- Each package/app/service gets its own sub_agent with `"path"` pointing to its directory
- Shared packages (`libs/`, `shared/`, `common/`) get a dedicated `shared-lib` sub_agent
- Build commands run from the workspace root using the workspace manager

### Multi-repo microservices
- Each service repo gets its own sub_agent with `"path"` pointing to its directory
- One `api-gateway` sub_agent if a gateway exists
- Shared libraries (published packages) are treated as 3rd party dependencies

### Hybrid
Combine the above — monorepo sub_agents for the monorepo, separate sub_agents with paths for standalone repos.

## Shared code rules (monorepo and multi-repo)

Load these rules when any task touches `shared/`, `libs/`, `common/`, or a package consumed by multiple services:

1. **Breaking changes require all consumers to be updated in the same PR sequence** — never leave a consumer broken between PRs
2. **The `@backend` agent must confirm which services consume the shared code** before making any interface change
3. **Shared code changes are always PR 1** — consumer updates follow in subsequent PRs
4. **Shared code has stricter test requirements** — every exported interface must have tests; coverage cannot drop

## Cross-service task routing

When a task spans multiple services, the orchestrator sequences work in dependency order.
For sequencing rules and PR ordering: read `references/cross-service-tasks.md`

## Record in project-overview

After detection, record under `## Architecture topology`:
```markdown
## Architecture topology
- Type: [Single / Monorepo / Multi-repo microservices / Hybrid]
- Workspace manager: [Nx / Turborepo / pnpm / Maven multi-module / none]
- Services: [list with paths]
- Shared packages: [list with paths, or "none"]
- API gateway: [path or "none"]
```