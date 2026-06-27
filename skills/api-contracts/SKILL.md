---
name: api-contracts
description: API contract design, versioning, breaking change rules, and 3rd party integration patterns. Loaded by the API agent and architect.
---

# API Contracts

## Contract-first principle
Define the contract before writing implementation code. The contract is the source of truth — both FE and BE implement against it.

## REST / OpenAPI
- Spec lives in a committed file (e.g. `docs/api/openapi.yaml` or `src/main/resources/openapi.yaml`).
- Use semantic versioning for the API: `/v1/`, `/v2/`.
- Generate server stubs and client types from the spec — do not hand-write them.

### Endpoint design rules
- Nouns for resources, verbs via HTTP method: `GET /users`, `POST /users`, `DELETE /users/{id}`
- Consistent error shape across all endpoints:
```json
{
  "error": "RESOURCE_NOT_FOUND",
  "message": "User with id 42 does not exist",
  "timestamp": "2024-01-01T00:00:00Z"
}
```
- Use 422 (Unprocessable Entity) for validation errors, not 400.
- Pagination on all list endpoints: `?page=0&size=20` with a consistent response wrapper.

## GraphQL
- Schema-first: define `.graphql` schema files before writing resolvers.
- Breaking changes (removing fields, changing types) require a deprecation period.
- Use `@deprecated(reason: "...")` for at least one release before removal.
- Subscriptions must have documented error and reconnection behavior.

## Breaking vs non-breaking changes

| Change | Classification |
|---|---|
| Add optional field | Non-breaking |
| Add new endpoint / query | Non-breaking |
| Remove field or endpoint | **Breaking** |
| Rename field | **Breaking** |
| Change field type | **Breaking** |
| Change required → optional | Non-breaking |
| Change optional → required | **Breaking** |

**Breaking changes require architect approval and a versioning strategy before implementation.**

## 3rd party integrations

### Required for every integration
- Error handling for all documented failure modes
- Timeout configuration (never rely on defaults)
- Retry policy with exponential backoff for transient failures
- Circuit breaker or fallback if the service is on the critical path
- API key / secret stored in environment variables — never committed

### Integration structure (backend)
```
infrastructure/
└── [service-name]/
    ├── [ServiceName]Client.java       # HTTP/SDK client wrapper
    ├── [ServiceName]Config.java       # configuration and bean setup
    ├── [ServiceName]Dto.java          # request/response models
    └── [ServiceName]ClientTest.java   # unit tests with mocked HTTP
```

### New 3rd party service checklist
- [ ] Developer approval obtained (see `third-party-policy`)
- [ ] Error handling implemented
- [ ] Timeout configured
- [ ] Retry logic implemented
- [ ] Secrets stored in env vars
- [ ] Integration documented in `docs/architecture.md`
