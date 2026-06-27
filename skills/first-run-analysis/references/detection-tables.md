# Detection Reference Tables

## Backend detection signals

| Category | What to detect |
|---|---|
| **Language** | Java, Kotlin, TypeScript/Node, Python, Go, C#, Ruby, PHP |
| **Framework** | Spring Boot, Express, FastAPI, Django, Rails, ASP.NET, NestJS |
| **Build tool** | Maven (`pom.xml`), Gradle (`build.gradle`), npm, pip, cargo |
| **Test framework** | JUnit 5, Mockito, pytest, Jest, RSpec, Go test |
| **Linter** | Checkstyle, SpotBugs, PMD, Detekt, ktlint, SonarQube, Klocwork |
| **Database** | PostgreSQL, MySQL, MongoDB, Redis, H2, SQLite |
| **ORM** | JPA/Hibernate, Prisma, SQLAlchemy, ActiveRecord, GORM |
| **Migration tool** | Flyway, Liquibase, Alembic, Knex |
| **API style** | REST, GraphQL, gRPC, tRPC |
| **Auth** | JWT, OAuth2, session-based |
| **CI/CD** | GitHub Actions, Azure Pipelines, Jenkins, GitLab CI |
| **Containers** | Docker, docker-compose, Kubernetes |

## Frontend detection signals

| Category | What to detect |
|---|---|
| **Language** | TypeScript, JavaScript |
| **Framework** | React, Vue, Angular, Svelte, Next.js, Nuxt |
| **Build tool** | Vite, Webpack, Parcel, esbuild |
| **State management** | Redux, Zustand, MobX, Recoil, Context API |
| **API client** | Apollo Client, TanStack Query, SWR, Axios |
| **UI library** | Tailwind CSS, shadcn/ui, MUI, Ant Design, Chakra |
| **Test framework** | Vitest, Jest, Testing Library |
| **Linter** | Biome, ESLint, Prettier |
| **i18n** | react-i18next, react-intl, lingui |
| **Mobile** | Capacitor, Expo, React Native |
| **Package manager** | npm, yarn, pnpm, bun |

## Topology detection signals

> Full topology detection and confirmation flow is in the `repo-topology` skill. The tables below are a quick reference.

### Monorepo signals
| Signal | Tool |
|---|---|
| `nx.json` or `nx` in devDependencies | Nx |
| `turbo.json` or `turbo` in devDependencies | Turborepo |
| `pnpm-workspace.yaml` | pnpm workspaces |
| `packages/`, `apps/`, `libs/` at root | Generic monorepo |
| Multiple `pom.xml` under one `.git` | Maven multi-module |
| `settings.gradle` with `include` | Gradle multi-project |

### Microservice signals (multi-repo)
| Signal | Location |
|---|---|
| Multiple sibling folders each with `.git` | workspace root |
| `docker-compose.yml` with multiple app services | workspace or any repo |
| Kubernetes manifests (`k8s/`, `helm/`) | any repo |
| API gateway config (Kong, Nginx, Traefik) | any repo |
| `application.yml` with `spring.cloud` | BE repos |

## Repo state signals

| State | Signals |
|---|---|
| **New** | No source beyond scaffolding, no business logic |
| **Partial** | Some source files, incomplete features, few/no tests |
| **Mature** | Substantial codebase, clear conventions, CI configured |

## Convention evaluation severity

| Severity | Condition | Action |
|---|---|---|
| 🔴 High | Violates SOLID/Clean Code AND inconsistent | Refactoring plan — immediate |
| 🟡 Medium | Inconsistent within the project | Refactoring plan — before next feature |
| 🟡 Medium | Violates principles but applied consistently | Refactoring plan — phased |
| 🔵 Low | Minor style inconsistency | Note in project-overview only |
| ✅ Pass | Consistent and follows principles | Record as established pattern |