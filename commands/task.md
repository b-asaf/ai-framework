---
description: Start a new task — runs Check 1 (first-run), Check 2 (branch guard), then the full product-manager → architect → plan-reviewer → implementation flow.
---

Start a new development task. Follow this sequence exactly:

1. Run Check 1: read `project-overview/sub/stack.md`. If it contains `[XXX]`, run first-run analysis first.
2. Run Check 2: propose a branch name, wait for confirmation, create the branch.
3. Load `instructions/AGENTS-reference.md` for the routing table.
4. Route to `@product-manager` for requirements grill (including necessity check).
5. Route to `@architect` for HLD and PR breakdown.
6. Route to `@plan-reviewer` to validate the plan.
7. On approval, implement one PR at a time.
8. After each PR: linter → code-reviewer → qa → gatekeeper.
