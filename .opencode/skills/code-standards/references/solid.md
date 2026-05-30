# SOLID — Reference

## S — Single Responsibility
Each class, module, or component has exactly one reason to change. If it handles both data fetching and rendering, split it. If it handles both business logic and persistence, split it.

## O — Open / Closed
Open for extension, closed for modification. Add behaviour by extending (new classes, new interface implementations), not by editing existing working code.

## L — Liskov Substitution
Subtypes must be substitutable for their base types without altering correctness. Overrides must honour the base contract — do not weaken preconditions or strengthen postconditions.

## I — Interface Segregation
No class should implement methods it does not use. Prefer many small focused interfaces over one large general-purpose one.

## D — Dependency Inversion
High-level modules must not depend on low-level modules. Both should depend on abstractions. Inject dependencies — do not instantiate them inside the class that uses them.