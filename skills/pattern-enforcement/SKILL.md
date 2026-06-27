---
name: pattern-enforcement
description: Discovers, enforces, and evolves project patterns. Run before writing any file in a domain. Re-runs whenever a new technology, protocol, or module type is encountered — not just on first run. Loaded by all implementation agents, architect, code-reviewer, and qa.
---

# Pattern Enforcement

## Core principle

Before writing any file, an agent must know the established pattern for that domain in this project. Patterns are not assumed from general knowledge — they are discovered from the actual codebase and recorded in `project-overview` under `## Discovered patterns`.

---

## When to run discovery

Discovery runs on **every new domain encountered**, not just on first run:

| Trigger | Example |
|---|---|
| First run | No patterns recorded yet |
| New protocol or technology | Project uses GraphQL, new feature needs REST |
| New file type | First migration file, first background job, first webhook handler |
| New module or bounded context | First feature in a new package, new service directory |
| Unfamiliar folder or structural pattern | Agent encounters a directory structure it hasn't seen in this project |
| Pattern registry entry is missing for the current task | Agent checks `project-overview` and finds no entry for this domain |

Discovery is **scoped** — only the specific domain that triggered it is scanned. Existing entries are not invalidated. Both GraphQL and REST patterns can coexist in the registry.

---

## How to run discovery

1. **Check the registry first.** Read `## Discovered patterns` in `project-overview`. If an entry exists for this domain and its status is `following` or `approved-new`, use it directly — do not re-scan.

2. **If no entry exists**, scan the codebase for this domain:
   - Find 3-5 existing files of the same type
   - Identify the consistent pattern (location, naming, structure)
   - Determine if the pattern is consistent across the codebase or mixed

3. **Evaluate the found pattern** against clean code and SOLID principles (see `code-standards` skill).

4. **Apply the correct outcome** (see below).

5. **Update the registry** in `project-overview` with the finding.

---

## The three outcomes

### Outcome 1 — Pattern found, follows best practice → enforce it

Follow the pattern exactly. No deviation, no "improvement" without developer approval.

Update the registry:
```
| [domain] | [pattern description] | [example file] | following |
```

### Outcome 2 — No pattern found (new domain or new project)

Do not invent a pattern silently. Notify the developer and propose an approach:

```
⚠️ No existing pattern found for: [domain]

This appears to be the first [REST endpoint / migration / background job / etc.] in this project.

Proposed approach (based on best practice):
- File location: [proposed path]
- Naming convention: [proposed convention]
- Structure: [proposed structure]
- Rationale: [why this follows clean code / SOLID]

Do you approve this pattern? It will be recorded and enforced for all future files of this type.
```

Wait for explicit developer approval before writing any file. Once approved, record it in the registry with status `approved-new`.

### Outcome 3 — Pattern found but violates SOLID or clean code

Do not silently follow a bad pattern. Notify the developer:

```
⚠️ Existing pattern found for: [domain] — but it has issues

Current pattern: [description]
Example: [file path]

Issues detected:
- [violation] — e.g. "Services directly instantiate repositories (violates Dependency Inversion)"
- [violation] — e.g. "Test files mixed with source files with no consistent naming"

Proposed replacement (best practice):
- [proposed pattern]
- Migration impact: [what would need to change in existing files]

Options:
1. Adopt the new pattern for new files only (existing files unchanged for now)
2. Adopt the new pattern and migrate existing files in a separate chore: PR
3. Keep the existing pattern for now (recorded as accepted-deviation)

Which do you prefer?
```

Wait for explicit developer choice. Record the outcome in the registry.

---

## Pattern registry format

Stored in `project-overview` under `## Discovered patterns`:

```markdown
## Discovered patterns

| Domain | Pattern | Example | Status |
|---|---|---|---|
| Test files (FE) | Co-located `.test.ts` next to source file | `src/hooks/useUser.test.ts` | following |
| Test files (BE) | Mirror package under `src/test/java/` | `src/test/java/com/app/service/UserServiceTest.java` | following |
| API protocol | GraphQL via Apollo | `src/graphql/schema.graphql` | following |
| API protocol | REST for file transfer | `src/api/upload/` | approved-new |
| Component structure | Feature folder with index | `src/features/users/index.tsx` | following |
| Error handling (BE) | `@ControllerAdvice` global handler | `src/controllers/GlobalExceptionHandler.java` | following |
| Import style (FE) | `@/` alias, no `../` | `import { useUser } from '@/hooks/useUser'` | following |
| Service layer | Interface + impl pair | `UserService.java` + `UserServiceImpl.java` | accepted-deviation |
```

**Status values:**
- `following` — pattern discovered and in use, agents enforce it
- `approved-new` — no prior pattern, developer approved this as the new standard
- `accepted-deviation` — pattern violates best practice but developer chose to keep it
- `pending` — pattern flagged, awaiting developer decision

---

## Domain-specific discovery guidance

### Test file placement
Scan for existing test files and determine:
- Are they co-located with source? (`useUser.test.ts` next to `useUser.ts`)
- Are they in a dedicated folder? (`__tests__/`, `test/`, `src/test/`)
- Do BE tests mirror the source package structure?
- Is naming consistent? (`.test.ts`, `.spec.ts`, `Test.java`, `Spec.java`)

Record whichever is found. If mixed, flag as Outcome 3.

### API protocol
Scan for existing API patterns:
- GraphQL: schema files, resolvers, `@Query`/`@Mutation` annotations
- REST: `@RestController`, `@GetMapping`, OpenAPI spec files, `fetch`/`axios` calls with path strings
- gRPC: `.proto` files, generated stubs

If a new protocol is introduced alongside an existing one (e.g. REST added to a GraphQL project), always trigger Outcome 2 — get developer approval for where and how the new protocol files live before writing anything.

### Component/module structure
Scan for how components or modules are organised:
- Flat: all components in one `components/` folder
- Feature-folder: `features/users/UserCard.tsx`, `features/users/useUsers.ts`
- Domain-driven: `domain/users/`, `domain/orders/`

### Import style
Scan for import patterns in existing source files:
- Path aliases (`@/`, `@app/`, `~`)
- Relative imports (`../`, `./`)
- Mixed (flag as Outcome 3 if inconsistent)

### Service and repository naming
Scan for naming conventions in the service layer:
- Suffix style: `UserService`, `UserRepository`, `UserMapper`
- Interface + impl: `UserService` interface + `UserServiceImpl` class
- Single class, no interface

### Error handling
Scan for how errors are handled across the layer boundaries:
- Global exception handler vs per-controller try/catch
- Typed error classes vs generic exceptions
- Error response shape consistency