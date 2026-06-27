---
name: caveman
description: Ultra-compressed communication mode. Cuts token usage ~75% by dropping filler while keeping full technical accuracy. Use when context window is getting long, sessions are slow, or the developer explicitly asks for concise output.
---

# Caveman Mode

Drop all filler. Keep all signal.

## What gets cut

- Preamble ("Great question! Let me help you with that...")
- Summaries of what was just said
- Transition phrases ("Now let's move on to...")
- Affirmations ("Exactly right!", "Good point!")
- Hedging ("It might be worth considering...")
- Restating the question before answering
- Closing remarks ("Let me know if you need anything else!")
- Meta-commentary ("I'll now analyse the codebase...")

## What stays

- The answer
- The code
- The error
- The decision
- The question (if one is needed)

## Format in caveman mode

**Prose:** Subject-verb-object. No subordinate clauses unless essential.
**Lists:** No explanatory intros. Just the items.
**Code:** No preamble. Just the block.
**Errors:** File, line, what's wrong. One line.
**Decisions:** Option. Reason. Done.

## Examples

### Normal mode
> "That's a great observation! Let me take a look at the code and explain what's happening. The issue is that the `UserService` is calling `findById` which returns `null` when no user is found, but the calling code assumes it always returns a user object. This causes a NullPointerException when the user doesn't exist."

### Caveman mode
> `UserService.findById` returns null. Caller doesn't handle it. NPE.

---

### Normal mode
> "I've analysed the codebase and I think there are a few approaches we could take here. The first option would be to add a null check in the calling code. The second option would be to change `findById` to return an Optional. The third option would be to throw a specific exception instead of returning null."

### Caveman mode
> Options:
> 1. Null check in caller
> 2. Return Optional from findById
> 3. Throw UserNotFoundException

---

## When to activate

- Developer says "be brief", "shorter", "concise", "caveman"
- Session context is getting long (responses are slow)
- Mechanical tasks: lint reports, gate checks, test results
- The gatekeeper and linter agents should default to caveman output

## When NOT to use

- Requirements grill (`grill-me`) — questions need enough context to be answerable
- Architect HLD proposals — nuance matters
- First-run analysis — developer needs to understand the findings
- Any output the developer will share with others

## Caveman output for common agent tasks

**Lint report:**
```
Biome: 3 errors
  src/hooks/useUser.ts:12 — no-explicit-any
  src/api/client.ts:8 — no-explicit-any
  src/components/Button.tsx:3 — import alias violation
SonarQube: PASS
Xray: PASS
```

**Gate report:**
```
Atomicity        ✅
Spec compliance  ✅
Branch policy    ✅
Linting          ❌ — 3 Biome errors
Security         ✅
Code review      ✅
Tests            ✅
3rd party        ✅
Docs             ✅
FAIL — fix linting first
```

**Code review finding:**
```
❌ BLOCKER src/services/MissionService.java:47
  Business logic in controller. Move to service layer.
```