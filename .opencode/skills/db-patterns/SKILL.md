---
name: db-patterns
description: Database schema design, migration strategy, repository patterns, and query conventions. Loaded by the DB agent and architect.
---

# Database Patterns

## Repository pattern
The repository layer is the **only** place that interacts with the database. Services never write queries directly.

```
Service → Repository interface → Repository implementation → Database
```

- Repository interfaces are defined in the domain layer.
- Repository implementations live in the infrastructure layer.
- Services depend on the interface, not the implementation (Dependency Inversion).

## Schema design rules
- Every table has a surrogate primary key (`id` — auto-increment or UUID).
- Use UUIDs for IDs exposed in APIs (never expose auto-increment integers externally).
- All timestamps: `created_at`, `updated_at` on every table. Use UTC.
- Soft deletes preferred over hard deletes for auditable entities: `deleted_at` nullable timestamp.
- Foreign keys must always have a corresponding index.
- Index every column used in a `WHERE`, `JOIN ON`, or `ORDER BY` clause.
- Column names: `snake_case`. Table names: `snake_case`, plural (`users`, `payment_transactions`).

## Migration rules
- One migration file = one concern (same as atomic-changes for code).
- Migrations are always additive first — never destructive in the same step.
- **Multi-step strategy for breaking changes:**
  1. Add new column (nullable)
  2. Backfill data
  3. Add NOT NULL constraint
  4. Remove old column (separate PR, after confirming no reads)
- Migration files are committed and never edited after merging.
- Naming: `V{timestamp}__{description}.sql` (Flyway) or equivalent.

## Query conventions
- Prefer ORM/query builder for standard CRUD.
- Use raw SQL only for complex queries that the ORM handles poorly — and document why.
- Never use `SELECT *` — always specify columns.
- Paginate all list queries — never return unbounded result sets.
- Use database-level constraints (NOT NULL, UNIQUE, CHECK) — do not rely solely on application validation.

## ORM-specific rules (detected from project)
If ORM is detected, apply its conventions from `project-overview`. Common rules:
- **JPA/Hibernate:** Use `@ManyToOne` with `fetch = LAZY` by default. Avoid N+1 with `@EntityGraph` or JPQL joins. Never use `CascadeType.ALL` without understanding the implications.
- **Prisma:** Use `select` to limit returned fields. Prefer transactions for multi-step writes.
- **TypeORM / Sequelize:** Follow the repository pattern — do not use `Entity.find()` directly in services.

## Testing the persistence layer
- Unit test repositories with an in-memory database (H2 for JPA, SQLite for others) or test containers.
- Do not mock the database in repository tests — test real queries against a real schema.
- Verify migrations run cleanly in CI against a clean database.
