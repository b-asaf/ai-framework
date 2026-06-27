---
name: testing-strategy
description: Test writing conventions, what to test, and coverage expectations. Loaded by the QA agent.
---

# Testing Strategy

## What to test — always

For every new implementation, tests must cover:

| Scenario | Priority |
|---|---|
| Happy path — expected successful behavior | Required |
| Edge cases — boundary values, empty, null, max | Required |
| Error paths — invalid input, service failures, auth errors | Required |
| Behavior, not implementation — test *what*, not *how* | Required |
| Side effects — verify the right calls were made (with mocks) | When relevant |

## What NOT to test
- Framework internals (don't test that Spring wires beans correctly)
- Trivial getters/setters with no logic
- Auto-generated code

---

## Frontend testing conventions

### Unit tests (component / hook / utility)
- Co-locate with the file being tested: `MyComponent.test.tsx` alongside `MyComponent.tsx`
- Use Testing Library — query by role, label, or text. Avoid `getByTestId` except as a last resort.
- Use `userEvent` (not `fireEvent`) for user interactions.
- Mock API calls — do not hit the real backend in unit tests.

```typescript
describe('UserCard', () => {
  it('displays the user name', () => { ... })
  it('calls onDelete when delete button is clicked', async () => { ... })
  it('shows an error state when user data is missing', () => { ... })
})
```

### Integration tests
- Test a full page or feature flow with mocked API responses.
- Verify that components wire together correctly.

---

## Backend testing conventions

### Unit tests (service / repository / utility)
- One test class per production class, in the mirror package under the test root.
- Use mocks for all dependencies — unit tests must not hit a database or network.
- Follow given / when / then structure.

```java
@Test
void shouldReturnUserWhenFound() {
    // given
    given(userRepository.findById(1L)).willReturn(Optional.of(user));

    // when
    var result = userService.findById(1L);

    // then
    assertThat(result).isPresent();
    assertThat(result.get().getName()).isEqualTo("Alice");
}
```

### Integration tests
- Test the full layer stack (controller → service → repository) with a real or in-memory database.
- Use `@SpringBootTest` (Spring) or equivalent for wiring.
- Cover the happy path and key error responses.

### Test naming
- `shouldDoXWhenY` or `givenXWhenYThenZ`
- Names must describe behavior, not implementation

---

## Coverage expectations
- **Minimum:** no coverage regression — new code must not lower overall coverage.
- **Target:** 80%+ line coverage on service and utility classes.
- **Not required:** 100% coverage on DTOs, config classes, or generated code.

Always report coverage delta (before → after) in the QA report.