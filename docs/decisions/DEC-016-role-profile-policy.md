# DEC-016 — Role, profile and policy separation

**Status:** Accepted. Supersedes the ownership model of DEC-011; DEC-011 is marked "superseded by DEC-016" in step 4.3 of `docs/transition-plan.md`.
**Date:** 2026-10-06

## Context

- Role, prompt, permissions and model are fused in `agents/*.md`, and model assignments are also kept in `MODEL-ASSIGNMENT-MATRIX.md`.
- DEC-014 documents three incidents that follow from this: the same model assigned to planner and plan-reviewer, an experimental model assigned without evaluation, and a gatekeeper tier decided by hand.
- The reviewer spike showed that a model swap needs only a profile change (reviewer GPT vs Claude, same role, runner and gates) (F12).
- Permissions are default-allow, the last matching rule wins, and delegation through `task` bypassed `write: deny` (F4, F5).

## Options considered

- **Option A: keep the model in agent frontmatter and in the matrix.** No work. Causes the DEC-014 incidents.
- **Option B: capability-based routing with a capability catalog.** Flexible, but there are few roles and a closed model set today. Deferred until explicit mapping becomes painful.
- **Option C: a declarative workflow definition replacing the orchestrator.** Deferred. Phase 3C is a hardcoded, throwaway experiment instead.
- **Option D: a new repository.** Rejected: it duplicates `setup.py`, the symlinks, the hooks and the DEC history.
- **Option E: separate role, profile and policy in this repo, OpenCode only, with generated agents.** Chosen.

## Decision

### Four concerns, four homes

| Concern | Home |
|---|---|
| Role: responsibility, prompt, access intent | `roles/<role>.json`, `roles/<role>.prompt.md`. No model, no concrete runtime permissions |
| Model selection | `execution/profiles/*.json` |
| Constraints: allowed models, families, experimental status, independence, protected paths | `execution/policy.json`, enforced by code |
| Verification facts | `verification/checks` and `verification/gates` (DEC-015) |

### Access intent versus runtime permissions

A role states an intent, for example `access: read-only`. The OpenCode adapter translates it into concrete deny rules (`edit`, `write`, `task`, and `bash` deny or a tight allow-list). The validator checks the derived output, not the intent alone.

### Policy shape and families

`policy.json` is grouped into `models` and `constraints`. `family` names the model lineage (`claude`, `gpt`, `gemini`; Codex models are `gpt`) and is independent of provider. The independence rule compares families, not providers. Protected paths are versioned data in `constraints` and are enforced by comparing the working tree before and after a run.

### Contracts and artifact ownership

`execution/schemas/` are the contracts between stages. Stages hand off through artifacts that validate against them, never through implicit agent context.

| Artifact | Owner |
|---|---|
| `review.json` | `reviewer` |
| `qa.json` | `qa` |
| Verification results | `verification/` |
| `RunRecord` | runner |

No stage modifies another stage's artifact.

### Success levels and RunRecord

| Level | Question | Decided by |
|---|---|---|
| Execution | Did OpenCode run to a normal stop? (`text` event, `reason: "stop"`, no `error` event) | adapter |
| Artifact | Is there a valid report that matches the schema? | `report.py` |
| Workflow | Do the report and the deterministic gates satisfy the requirements? | gates |

`RunRecord` minimum fields: `run_id`, `timestamp`, `role`, `profile`, `runtime`, `requested_model`, `resolved_model`, `policy_result`, `fallback`, `input_artifacts`, `output_artifacts`, `status`, `stop_reason`, `tokens`, `cost`, `duration_ms`, `verification`, `error`.

### Provider boundary

- The runtime is OpenCode only. OpenCode-specific knowledge stays in `opencode_adapter.py`, the access-to-permission translation and `opencode_models.py`.
- `roles/` and `verification/` contain no concrete model ids or provider names.
- Claude, GPT and Gemini families must all stay usable, and a model swap changes only the profile.
- A second adapter is deferred until agents must run outside OpenCode. Its interface stays at three functions: derive agent, run, parse events.

### Generated files

In Phase 4, `agents/*.md` and `MODEL-ASSIGNMENT-MATRIX.md` are generated from roles, profile and policy. They stay committed so a fresh clone works if generation fails. They are never edited by hand, and the validator detects drift.

Touches: `agents/*.md`, `MODEL-ASSIGNMENT-MATRIX.md`, `tools/validate_agents.py`, `setup.py`, and the new `roles/`, `execution/` and `adws/` folders.

## Reasoning

1. **Agent or deterministic?** Whether a model choice is legal (family, experimental status, independence) is deterministic, so policy checks it in code before any model call. The role prompt and the review itself stay with the agent.
2. **Trade-offs.** A new role needs 3 small files instead of 1, and a runner, a generator and policy files must be maintained. In return, the validator catches a bad model choice before anything runs. The Phase 2 gate decides whether to continue past Phase 1.
3. **Cheaper way?** A single config file for models, kept next to the current agents. That is the fallback if the Phase 2 gate fails, and the Phase 1 validator rules already deliver most of the DEC-014 protection.
4. **What a developer can now see or do.** Change which model runs a role by editing one profile entry. See why a model actually ran, from the `RunRecord`. Get a clear rejection when a profile breaks a rule.

## Consequences

- A new role touches at most 3 files (`roles/x.json`, `roles/x.prompt.md`, a profile entry), and the validator catches a misconfiguration.
- The global OpenCode config links into this repo (F16), so generated agents go live on `git pull`. Phases 3A and 4 are verified in a throwaway clone before the PR is merged.
- It is still open whether all 15 agents migrate to `roles/` or only the runner roles. Decide at the Phase 2 gate.
- Open decisions from the plan: #1 which paths implementation roles may write (before Phase 2 ends), #2 hooks in Python (before 3A), #4 profile location (before Phase 4), #5 parity margin (before Phase 2 ends).
- Evidence: `tests/bench/permissions-evidence.md`, `tests/bench/git-permissions-evidence.md`, and findings F4, F5, F9, F12 and F16 in `docs/transition-plan.md`.
