# DEC-026 — One folder for the files the framework generates in a project

**Status:** Accepted
**Date:** 2026-11-20

## Context

- `first-run-analysis` writes into a project: the populated copy of the `project-overview` skill (`docs/project-overview/`), `docs/refactoring-plan.md`, `.ai-framework.json`, and in step 7 also `CONTEXT.md` and `_opencode.json`, with instructions to touch `Manual.md` and `workflow-guide.md`. They sit in the repository root and in `docs/`.
- Decision #14 (2026-11-14): everything the framework generates in a project lives in one folder, and the developer can change where it is, through a key in `.ai-framework.json`, which stays at the repository root (the setting cannot live inside the folder it points to).
- Who reads the paths (read 2026-11-20): code in `execution/runner/` (`preflight.py` holds the stack path, `run.py` the `qa` task message, `bench_cases.py` and `qa_cases.py` write fixtures there) and six test files; text in `AGENTS.md` (Check 1 and rule 4), `first-run-analysis`, `commands/first-run.md`, `refactor-planner`, `improve-codebase-architecture` and the README. The hooks, the push gate and the scripts do not read these paths (`hooks/build-verify.sh` only names one in a comment).
- The developer's decision (2026-11-20): no migration command; in an existing project he moves or deletes the files himself.

## Options considered

- **A: leave the files where they are.** Rejected in decision #14.
- **B: one folder with a legacy fallback and a migration command** (the first sketch of S.12). Rejected: the fallback is a rule kept only to be deleted later, and the developer moves projects by hand.
- **C: one folder, a key that moves it, no fallback and no migration tool.** Chosen.
- **D: the key in a file inside the folder.** Rejected in decision #14.

## Decision

1. **The folder** is `.ai-framework/` at the repository root. The key `generatedDir` in `.ai-framework.json` (a relative path written with forward slashes) moves it, for example `"generatedDir": "docs/ai-framework"`.
2. **What moves in:** `docs/project-overview/` becomes `<dir>/project-overview/`, with its contents unchanged (a prefix change, so either spelling of the stack file survives), and `docs/refactoring-plan.md` becomes `<dir>/refactoring-plan.md`.
3. **What stays where it is.** Files a tool reads only at a fixed path: `.ai-framework.json` (also the home of the key), `opencode.json`, `AGENTS.md`, `CLAUDE.md`, `.github/copilot-instructions.md`. Files that belong to a workspace and not to one repository, and that people keep up to date by hand: `CONTEXT.md`, `CONTEXT-MAP.md` and `_opencode.json` (the `domain-model` skill puts `CONTEXT.md` at the workspace root, which in a multi-repo project holds several git repositories, and each has its own `.ai-framework.json`).
4. **One helper for code,** `execution/runner/generated_dir.py`: it reads `generatedDir` from the project's `.ai-framework.json`, falls back to `.ai-framework/`, and fails closed on a value that is not a string, is empty or `.`, is absolute (a leading slash or backslash, a drive letter, a UNC path), has a `..` segment, or resolves outside the repository. Its consumers are the runner preflight, the `qa` task message and the fixtures.
5. **Agents resolve the folder without a tool:** they read `.ai-framework.json` with the read tool and use `generatedDir` when it is present, otherwise `.ai-framework/`. A value that is absolute or has `..` stops the agent, which tells the developer. `AGENTS.md` Check 1 says this once, and the other files point to it.
6. **No fallback and no migration tool.** A project whose files are not at the resolved place fires the first-run gate (Check 1), and the runner preflight fails with a message that names the path it looked in. The developer moves the files (`mkdir .ai-framework`, then `git mv docs/project-overview .ai-framework/project-overview`; `git mv` needs the target folder to exist) or lets first-run write them again.
7. **Order of the changes** (one PR each): the helper (additive), then the runner consumers (preflight, `qa` task message, fixtures and tests), then the text consumers (the files listed in the context), then the README explanation and the framework's own move. The runner goes before the text because it is the lower-traffic consumer: between the two PRs a project works for agents and fails runner preflight, the other order would fire the first-run gate on every task. Projects are moved after the text PR.

Touches (planned): `execution/runner/generated_dir.py` (new), `execution/runner/preflight.py`, `execution/runner/run.py`, `execution/runner/bench_cases.py`, `execution/runner/qa_cases.py`, their tests, `AGENTS.md`, `skills/first-run-analysis/SKILL.md`, `commands/first-run.md`, `agents/refactor-planner.md`, `skills/improve-codebase-architecture/SKILL.md`, `README.md`.

## Reasoning

1. **Agent or deterministic?** Where code reads the path (runner), a helper resolves it and fails closed. Where an agent reads it, an instruction does; the agent has no tool to enforce it, and the file is committed and written by the developer, so the risk is small.
2. **Trade-offs.** A project that is not moved stops at the first-run gate until the developer moves its files. That is the cost of having no fallback, and the developer chose it. `CONTEXT.md` stays outside the folder, so a project has generated files in two places, but only the ones that belong to one repository are grouped.
3. **Cheaper way?** A fallback to the old path would spare the developer the move and cost a rule that has to be deleted later.
4. **What a developer can now see or do.** One folder per project holds what the framework wrote, it can be moved with one key, and `.gitignore` or a review can treat it as one unit.

## Consequences

- Between the runner PR and the text PR a project works for agents and fails the runner preflight. Do not run the runner on a project in that window, and move projects only after the text PR.
- The text names two spellings of the stack file: `docs/project-overview/stack.md` (AGENTS.md, the preflight, this repository) and `sub/stack.md` (the skill table, and step 7 of `first-run-analysis`, which says to mirror the `sub/` folder); the runner fixtures write both. The folder moves as a whole, so neither is lost; S.12f (2026-11-23) settled it from the first-run output of two real projects, which have a flat `stack.md` and use `sub/` only for the other files: the text names `project-overview/stack.md`, and the skill template's `stack.md` moved up from `sub/`.
- Step 7 of `first-run-analysis` also names `Manual.md` and `workflow-guide.md`. No template for either exists in this repository, and the root `workflow-guide.md` is the framework's own guide. S.12d removed the `Manual.md` line (the developer's projects have none) and left the optional `workflow-guide.md` line.
- This repository is a project too: its own `docs/project-overview/` and `docs/refactoring-plan.md` moved in S.12e (`git mv`), together with the README explanation. S.12f settled the spelling of the stack file (see the point above).
- S.12b (the helper) refuses more shapes than point 4 lists: a backslash anywhere (the key is written with forward slashes), a colon, leading or trailing whitespace or a control character, a `.` or empty segment (a doubled or trailing slash) and a `.git` segment; a key that is present but `null` is refused. A missing `.ai-framework.json` gives the default, because the runner preflight reports the missing file by itself; a file that exists but cannot be read, or is not a JSON object, is refused. The agent rule of S.12d (point 5) names the same shapes in one sentence. S.12c adds a character rule to the helper: a folder name may hold only letters, digits, spaces and `.` `_` `-` `/`, so it can never carry a character that the task message of a headless run refuses (F10: quotes, pipes, braces and similar); the agent rule of S.12d says the same.
