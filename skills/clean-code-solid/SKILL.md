---
name: clean-code-solid
description: Use when writing, modifying, refactoring, designing, or reviewing code and architecture to apply the five SOLID principles at every scale — function, class, module, service.
---

# Clean Code — SOLID Principles

SOLID principles apply at every scale. The same question asked of a 10-line function and a 10-service system: does each unit have one reason to change? Can you add behaviour without editing existing code? Are dependencies on abstractions, not concretions?

---

## S — Single Responsibility Principle

**"A module should have one, and only one, reason to change."**

A *reason to change* is a person or role whose requirements drive the behaviour. A class that satisfies both the billing team and the report team has two reasons to change.

- At function level: a function that validates input *and* persists the result has two responsibilities — split it.
- At class level: if "and" is needed to describe what the class does, it does too much.
- Symptom: a file is edited frequently for unrelated reasons.

## O — Open/Closed Principle

**"Software entities should be open for extension, closed for modification."**

Adding new behaviour should be possible by *writing new code*, not by editing working code.

- An `if/else` or `switch` chain inside existing logic that grows every time a new variant is added is a violation — replace with polymorphism.
- A function with a `type` or `mode` parameter that changes execution path should be two functions, or should delegate to a strategy.
- Symptom: adding a new case requires editing every caller or conditional chain.

## L — Liskov Substitution Principle

**"Derived classes must be substitutable for their base classes."**

Any code that works correctly with a base type must work correctly with any subtype.

- Never override a method to throw `NotImplementedException` or to silently no-op it.
- Strengthen postconditions (do at least what the parent promised), never weaken them.
- Symptom: callers type-check with `instanceof` before using a subtype.

## I — Interface Segregation Principle

**"Clients should not be forced to depend on interfaces they do not use."**

Many narrow, focused interfaces beat one wide general-purpose one.

- Split interfaces by the distinct roles that consume them.
- A function that accepts a large object when it only uses one field has an ISP smell — pass the field.
- Symptom: a class implements an interface but leaves several methods as stubs or empty bodies.

## D — Dependency Inversion Principle

**"High-level modules should not depend on low-level modules. Both should depend on abstractions."**

Business logic must not be held hostage to infrastructure details.

- High-level policy defines *interfaces* (ports) expressing what it needs.
- Infrastructure implements those interfaces. The arrow of dependency points toward the domain, always.
- Never instantiate a concrete infrastructure type (`new PostgresRepository()`, `new StripeClient()`) inside business logic. Inject it.
- Symptom: a unit test for business logic requires a real database, HTTP server, or file system.

---

## Write-time checklist

| Check | Question |
|---|---|
| **SRP** | Does this unit have exactly one reason to change? |
| **OCP** | Can I add a new variant without editing this code? |
| **LSP** | If subclassed, can every subclass be dropped in without callers noticing? |
| **ISP** | Does every consumer of this interface use everything it exposes? |
| **DIP** | Does this unit depend on a concrete infrastructure type? |

Any "no" is a design problem to fix before submitting.

## Review cite format

All SOLID violations are **BLOCKING**.

- `[SOLID/SRP] <file>:<line or class> — has two responsibilities: <A> and <B>. Separate by <suggested boundary>.`
- `[SOLID/OCP] <file>:<line> — adding a new case requires editing this existing if/else chain. Extract a <strategy/interface>.`
- `[SOLID/LSP] <file>:<line> — <Subtype> throws NotImplemented / weakens contract of <Base>. Use composition or redesign the hierarchy.`
- `[SOLID/ISP] <file>:<line> — <Consumer> only uses <X> of the interface. Split the interface.`
- `[SOLID/DIP] <file>:<line> — <BusinessClass> directly instantiates <ConcreteInfrastructure>. Depend on an interface; inject the implementation.`

Do not produce vague findings like "possible SRP issue". Every finding names the two distinct responsibilities or the concrete dependency that should be inverted.
