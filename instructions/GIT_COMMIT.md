# GIT_COMMIT.md
> Commit message guidelines. Suggested to the developer by agents — never
> committed automatically.

---

## Format

```
<type>(<scope>): <short summary>

[optional body — wrap at 72 chars]

[optional footer — BREAKING CHANGE, closes #issue]
```

## Types

| Type       | When to use                                      |
| ---------- | ------------------------------------------------ |
| `feat`     | New feature visible to the user                  |
| `fix`      | Bug fix                                          |
| `refactor` | Code change that is not a feat or fix            |
| `chore`    | Build, deps, tooling — no production code change |
| `docs`     | Documentation only                               |
| `test`     | Adding or correcting tests                       |
| `ci`       | CI/CD pipeline changes                           |
| `hotfix`   | Urgent production fix                            |

## Rules

- Summary line: imperative mood, ≤ 72 chars, no period at the end
- Scope: the module, package, or layer affected — e.g. `users`, `api`, `db`
- Body: explain **why**, not what (the diff shows what)
- One concern per commit — matches one row in the architect's PR breakdown table
- Breaking changes: add `BREAKING CHANGE:` in the footer

## Examples

```
feat(users): add CSV export endpoint

Closes #142. Endpoint streams rows to avoid memory spikes on large datasets.

fix(auth): prevent token refresh race condition

Two concurrent requests could both receive a 401 and both attempt refresh,
resulting in one getting a 403. Added a mutex on the refresh path.

chore(deps): upgrade Spring Boot to 3.3.1

Resolves CVE-2024-38809. No API changes.
```
