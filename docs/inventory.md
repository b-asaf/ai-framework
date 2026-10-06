# Framework inventory (step 0.3)

Date: 2026-10-03. Status: **provisional**.

Basis for the labels: line counts, behavior observed in steps 0.5 and 0.6 (see `tests/bench/permissions-evidence.md` and `tests/bench/git-permissions-evidence.md`), and the hook warnings seen on real pushes. File contents were not read line by line. Each "Confirm" note says what to read when the phase that touches the file starts. Nothing is deleted before Phase 4.

Labels: **KEEP** (unchanged), **MOVE** (logic goes elsewhere), **SPLIT** (becomes several parts), **REPLACE** (rewritten), **REMOVE** (deleted in Phase 4 after a check).

## 1. Files listed in plan step 0.3

| File | Lines | Label | Phase | Notes |
|---|---|---|---|---|
| `hooks/pre-push` | 230 | SPLIT | 3A | Branch protection, diff-size and the verify gate move to `verification/checks/`; the hook becomes a thin entrypoint. All three skip silently when `origin/HEAD`, `protectedBranches`, `diffBaseBranch` or `.ai-framework.json` is missing (F14), so the new checks must fail closed. Observed: it blocks `HEAD:main` only when `origin/HEAD` is set |
| `hooks/build-verify.sh` | 98 | MOVE | 3A | Build and test facts go to `verification/checks/`. Stays shell or becomes Python per decision #2 |
| `hooks/pre-commit` | 15 | KEEP | revisit with decision #2 | Commit-time rules (no direct commits to `main`, branch prefixes) were observed at the first plan commit. Confirm whether the rule lives here or in `commit-msg` |
| `hooks/commit-msg` | 15 | KEEP | Phase 1 | Confirm which message format it enforces before the first Phase 1 commit |
| `hooks/install-hooks.sh` | 21 | KEEP | confirm | Check its overlap with `add_git_template` in `setup.py`. A fresh test repo contained each hook plus a `.bak` copy (observed in step 0.6), so find out why |
| `hooks/session-end.js` | 0 | REMOVE | 4 | Empty file. Confirm that nothing references it, then delete it in Phase 4 |
| `agents/gatekeeper.md` | 139 | SPLIT | 3A.4 | Deterministic items move to `verification/`; judgment-only items stay. Then decide whether the tier can drop |
| `tools/validate_agents.py` | 533 | SPLIT | 1.3 to 1.8 | Becomes `validate_framework.py` plus `tools/lib/frontmatter.py` and `tools/lib/opencode_models.py`. The 16 cross-family edges move to `policy.json` (`constraints.independence`). `validate_agents.py` stays as a wrapper |
| `setup.py` | 864 | KEEP | 4.2 | Small additions only (run the generator, link `adws/` if needed). Large file, so no refactor. The Windows copy fallback (`OUT OF DATE` warning) already exists |
| `AGENTS.md` | 223 | SPLIT | 1.9, 2 | Interactive workflow versus rules a headless run must satisfy. See section 4 |
| `opencode.json` | not counted | REPLACE (bash block) | 1.9 | Catch-all first, tighter patterns, allows for branch, commit and feature-branch push. The file is linked into `~/.config/opencode/`, so test it in a throwaway setup before merging (F16) |
| `.ai-framework.json` | not present | n/a | 3A | Not present in this repo (verified). It is a per-project file created by the first-run analysis. Without it, three pre-push checks skip silently on pushes from this repo. Decide in 3A whether the framework repo gets its own with `protectedBranches` and `diffBaseBranch` |

## 2. Agents (15 files)

| File | Label | Phase | Notes |
|---|---|---|---|
| `agents/code-reviewer.md` | KEEP | through Phase 2 | It is the benchmark baseline. Fix the backslash path in step 1.3. Replaced by the generated file in Phase 4 |
| `agents/qa.md` | SPLIT | 3B | Becomes `roles/qa.*` with the QAReport envelope |
| `agents/plan-reviewer.md` | SPLIT | 3B | Becomes `roles/plan-reviewer.*` |
| `agents/gatekeeper.md` | SPLIT | 3A.4 | See section 1 |
| `agents/orchestrator.md` | KEEP | 4 | Workflow replacement is deferred. Frontmatter generated in Phase 4 if it gets a role |
| `api.md`, `architect.md`, `backend.md`, `db.md`, `frontend.md`, `frontend-error-fixer.md`, `product-manager.md`, `refactor-planner.md`, `ui.md`, `web-research-specialist.md` | KEEP | 1, 4 | Validator rules from steps 1.5 and 1.6 apply to all of them. They move to `roles/` only if there is a concrete need |

Open question for the Phase 2 gate: Phase 4 generates `agents/*.md` from `roles/`. Migrating only the runner roles leaves two sources of truth (hand-written and generated agents), while migrating all 15 is more work. Decide at the gate.

## 3. Global OpenCode config (`~/.config/opencode/`)

| Item | State | Label | Notes |
|---|---|---|---|
| `opencode.json`, `AGENTS.md`, `agents`, `commands`, `hooks`, `scripts`, `skills` | links into `/d/ai-framework` | KEEP | A `git pull` on `main` changes live behavior for every project (F16) |
| `opencode.jsonc` | 50 bytes, `$schema` only, not linked | KEEP | Not framework-owned. No action |
| `package.json`, `package-lock.json`, `node_modules` | dated before the framework links | KEEP | Appear to be OpenCode's own dependencies. Not framework-owned |
| `plugins/` | empty | n/a | Nothing to do |

New folders (`roles/`, `execution/`, `adws/`, `verification/`) are not linked. Add a link only if OpenCode must read them. Decide in Phase 2.

## 4. Headless handling of the `AGENTS.md` gates

Observed in step 0.5:

1. **First-run gate.** The agent stops when `docs/project-overview/stack.md` is missing or holds only a heading. An approval sentence in the task message does not bypass it.
2. **Own branch.** The agent creates a branch on its own.
3. **Plan confirmation.** The agent asks to confirm its plan before writing. An approval sentence in the task message bypasses it.

Decided on 2026-10-03, so that no second instruction set has to be maintained:
- The runner runs a **preflight check in code**. It requires `docs/project-overview/stack.md` with content and `.ai-framework.json`. If either is missing, the run fails with a readable message ("run the first-run analysis interactively once"). It never skips the check.
- The task message states the branch decision and the approval (section 6 of the plan, F8).
- There is no headless-specific `AGENTS.md`, so there is no second instruction set to maintain.

To confirm: read the gate text in `AGENTS.md`, and check that the approval sentence works for the GPT, Claude and Gemini families (only GPT was tested). Do the latter in step 2.5.

## 5. To confirm by reading

| Question | Command |
|---|---|
| Is `session-end.js` referenced anywhere? | `grep -rn "session-end" . -I \| grep -v "^./.git/"` and `git log --oneline -3 -- hooks/session-end.js` |
| Which hook enforces the main-branch and prefix rules? | `grep -n -i "not allowed" hooks/*` |
| What do the pre-push checks need? | `grep -n "protectedBranches\|diffBaseBranch\|ai-framework.json" hooks/pre-push` |
| Why do fresh repos contain `.bak` hooks? | `cat hooks/install-hooks.sh` and search `setup.py` for `add_git_template` |
