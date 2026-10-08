# DEC-016: Role, profile and policy separation

Status: Accepted. Supersedes the ownership model of DEC-011. DEC-011 is marked "Superseded by DEC-016" in step 4.3.
Date: 2026-10-06
Related: DEC-014, DEC-015, `docs/transition-plan.md`, `docs/inventory.md`

## 1. Context

- Role, prompt, permissions and model are fused in `agents/*.md`, and the model assignment is also kept in `MODEL-ASSIGNMENT-MATRIX.md`.
- DEC-014 documents three incidents that follow from this: the same model assigned to planner and plan-reviewer, an experimental model assigned without evaluation, and a gatekeeper tier decided by hand.
- The reviewer spike showed that a model swap needs only a profile change (reviewer GPT vs Claude, same role, runner and gates) (F12).
- Permissions are default-allow, the last matching rule wins, and delegation through `task` bypassed `write: deny` (F4, F5).

## 2. Decision

### 2.1 Four concerns, four homes

| Concern | Home |
|---|---|
| Role: responsibility, prompt, access intent | `roles/<role>.json`, `roles/<role>.prompt.md`. No model, no concrete runtime permissions |
| Model selection | `execution/profiles/*.json` |
| Constraints: allowed models, families, experimental status, independence, protected paths | `execution/policy.json`, enforced by code |
| Verification facts | `verification/checks` and `verification/gates` (DEC-015) |

### 2.2 Access intent versus runtime permissions

A role states an intent, for example `access: read-only`. The OpenCode adapter translates it into concrete deny rules (`edit`, `write`, `task`, and `bash` deny or a tight allow-list). The validator checks the derived output, not the intent alone.

### 2.3 Policy shape and families

`policy.json` is grouped into `models` and `constraints`. `family` names the model lineage (`claude`, `gpt`, `gemini`; Codex models are `gpt`) and is independent of provider. The independence rule compares families, not providers. Protected paths are versioned data in `constraints` and are enforced by comparing the working tree before and after a run.

### 2.4 Contracts and artifact ownership

`execution/schemas/` are the contracts between stages. Stages hand off through artifacts that validate against them, never through implicit agent context.

| Artifact | Owner |
|---|---|
| `review.json` | `reviewer` |
| `qa.json` | `qa` |
| Verification results | `verification/` |
| `RunRecord` | runner |

No stage modifies another stage's artifact.

### 2.5 Success levels and RunRecord

| Level | Question | Decided by |
|---|---|---|
| Execution | Did OpenCode run to a normal stop? (`text` event, `reason: "stop"`, no `error` event) | adapter |
| Artifact | Is there a valid report that matches the schema? | `report.py` |
| Workflow | Do the report and the deterministic gates satisfy the requirements? | gates |

`RunRecord` minimum fields: `run_id`, `timestamp`, `role`, `profile`, `runtime`, `requested_model`, `resolved_model`, `policy_result`, `fallback`, `input_artifacts`, `output_artifacts`, `status`, `stop_reason`, `tokens`, `cost`, `duration_ms`, `verification`, `error`.

### 2.6 Provider boundary

- The runtime is OpenCode only. OpenCode-specific knowledge stays in `opencode_adapter.py`, the access-to-permission translation and `opencode_models.py`.
- `roles/` and `verification/` contain no concrete model ids or provider names.
- Claude, GPT and Gemini families must all stay usable, and a model swap changes only the profile.
- A second adapter is deferred until agents must run outside OpenCode. Its interface stays at three functions: derive agent, run, parse events.

### 2.7 Generated files

In Phase 4, `agents/*.md` and `MODEL-ASSIGNMENT-MATRIX.md` are generated from roles, profile and policy. They stay committed so a fresh clone works if generation fails. They are never edited by hand, and the validator detects drift.

## 3. Alternatives considered

| Alternative | Outcome |
|---|---|
| Keep the model in agent frontmatter and the matrix | Rejected: causes the DEC-014 incidents |
| Capability-based routing and a capability catalog | Deferred until explicit mapping becomes painful |
| Declarative workflow definition replacing the orchestrator | Deferred. Phase 3C is a hardcoded, throwaway experiment |
| A new repository | Rejected: duplicates `setup.py`, symlinks, hooks and the DEC history |
| A second runtime adapter | Deferred until it is needed |

## 4. Consequences

- A new role touches at most 3 files (`roles/x.json`, `roles/x.prompt.md`, a profile entry), and the validator rejects a bad model choice before any model call.
- A runner, a generator and policy files are added. The Phase 2 gate decides whether to continue, and Phase 1 is valuable on its own.
- The global OpenCode config links into this repo (F16), so generated agents go live on `git pull`. Phases 3A and 4 are verified in a throwaway clone before the PR is merged.
- It is still open whether all 15 agents migrate to `roles/` or only the runner roles. Decide at the Phase 2 gate.

## 5. Open decisions

- #1: which paths implementation roles may write (before Phase 2 ends).
- #2: hooks in Python or shell calling Python (before 3A).
- #4: profile location, one default or a per-project override (before Phase 4).
- #5: parity margin for the Phase 2 gate (before Phase 2 ends).

## 6. Evidence

- `tests/bench/permissions-evidence.md` (step 0.5)
- `tests/bench/git-permissions-evidence.md` (step 0.6)
- Findings F4, F5, F9, F12 and F16 in `docs/transition-plan.md`
