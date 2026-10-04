# ai-framework transition plan: role / profile / policy separation

Status: proposed 2026-10-02, revised 2026-10-03 after review. Based on the Stage 0 feasibility tests and the reviewer spike (see `handoff.md`).

## 1. Goal and scope

**Goal.** Separate three things that are currently fused in `agents/*.md` and `MODEL-ASSIGNMENT-MATRIX.md`:

| Concern | Today | Target |
|---|---|---|
| Role (responsibility, access intent, prompt) | `agents/*.md` | `roles/<role>.json` + `roles/<role>.prompt.md`, no model, no concrete runtime permissions |
| Model selection | `model:` in agent frontmatter + matrix | `execution/profiles/*.json` |
| Constraints (allowed models, families, experimental status, independence, protected paths) | matrix prose + `validate_agents.py` | `execution/policy.json`, enforced by code |
| Verification facts (build, tests, branch, diff, dependency changes) | partly `gatekeeper` (LLM) | `verification/checks` + `gates`, run by code |

**Principle.** LLMs make judgments; code determines facts.

**Why (evidence, not theory).** DEC-014 documents three incidents: the same model assigned to planner and plan-reviewer, an experimental model assigned without evaluation, and a gatekeeper tier decided by hand. All three are preventable by a validated profile plus policy. The spike proved a model swap needs only a profile change (reviewer GPT vs Claude, same role, runner and gates).

**Runtime.** OpenCode only. The IDE Copilot uses `skills/` and the pre-push hook but does not run agents.

**Models.** Claude, GPT/Codex and Gemini families must all stay usable (directly or through the `github-copilot/` provider). Which model runs a role is a profile decision. Nothing framework-owned may assume Claude.

**Language.** Python, stdlib only. This is the current implementation choice (matches `setup.py` and `tools/`), not an architectural principle.

**Repository.** Same repo. A new repo would duplicate `setup.py`, symlinks, hooks and the DEC history.

### Working method

- **One short-lived branch per phase**, created in a separate worktree so the live install (which links into the main folder) is never disturbed:
  ```
  git worktree add ../ai-framework-new -b <branch>
  ```
  | Phase | Branch |
  |---|---|
  | 0 | `chore/phase-0-baseline` (plan, merged as PR #34), then `chore/phase-0-evidence` |
  | 1 | `chore/phase-1-hardening` |
  | 2 | `feat/phase-2-reviewer-runner` |
  | 3A | `feat/phase-3a-verification` |
  | 3B | `feat/phase-3b-roles` |
  | 3C | `feat/phase-3c-pipeline-experiment` |
  | 4 | `feat/phase-4-generated-agents` |
- **Repo hooks:** direct commits to `main` are blocked, and branch names need a prefix (`feat/ fix/ chore/ refactor/ docs/ hotfix/ release/`). Merging is done through a GitHub pull request, not a local merge.
- **Merge rule:** `main` is what is installed, so only merge what you would be comfortable having live today. Merge at phase exit, when the phase's exit test passes.
- **Phases that change live behavior (3A hooks, 4 generated agents):** verify in a throwaway clone with a fresh `setup.py` run before opening the PR.
- **Keep in sync:** `git merge main` into the phase branch if it lives longer than a few days.
- **Cleanup after each merge:** `git worktree remove ../ai-framework-new`, delete the local and remote branch (enable "Automatically delete head branches" on GitHub), then start the next phase from the updated `main`.
- **Shell:** Git Bash for all commands.

### Deliberately deferred (revisit only on a concrete trigger)

| Deferred | Trigger to revisit |
|---|---|
| Second runtime / provider adapter (for example running Codex CLI or Gemini CLI directly as agents) | You actually need to run agents outside OpenCode. The adapter interface stays at the three functions the runner already needs: derive agent, run, parse events |
| Capability-based routing and a capability catalog | Explicit mapping becomes painful across many roles |
| Workflow YAML / declarative pipeline definition replacing the orchestrator | Runner pipeline is stable and orchestrator duplication hurts. Phase 3C's hardcoded pipeline is an experiment, not the start of this |
| Visualizer / SQLite tracer | JSONL run records stop being enough |
| Provider factory, registry, executor abstractions | A second adapter exists |

## 2. Observed and tested findings

Status meaning: **verified** = observed in a test or spike run; **inferred** = deduced from config or a rule dump, to be tested in Phase 0; **unverified** = not checked, do not rely on it.

| # | Finding | Status | Design consequence |
|---|---|---|---|
| F1 | Headless `opencode run --format json` emits clean JSONL; `step_finish` carries tokens and cost | verified | `RunRecord` can log usage and cost |
| F2 | Exit code is 0 even when the agent did nothing (permission rejection, ask-then-stop) | verified | Never treat exit code 0 as success. Execution success = `text` event + `reason: "stop"` + no `error` event (see section 5.3 for the other two levels) |
| F3 | Hard failure (bad model id) gives exit 1 and a generic `error` event | verified | Validate model ids before running |
| F4 | Permissions are default-allow; the last matching rule wins | verified (bash rules) | Read-only roles need explicit `edit`, `write`, `task` deny, and `bash` deny or a tight allow-list; validator enforces. Evidence in `tests/bench/permissions-evidence.md` |
| F5 | Delegation through `task` bypassed `write: deny` until `task: deny` was added | verified | Deny `task` for read-only roles |
| F6 | `--agent X` on a `mode: subagent` agent silently falls back to the default agent (stderr warning only) | verified | Adapter derives primary-mode agent files; the warning is a hard failure |
| F7 | Tool names vary by model (`apply_patch` vs `edit`) | verified | Gates inspect the working tree, not tool names |
| F8 | Global `AGENTS.md` gates stop headless agents: (1) a first-run gate when `docs/project-overview/stack.md` is missing or only a heading, (2) the agent creates a branch on its own, (3) the agent asks to confirm its plan before writing | verified | A pre-approval sentence in the task message bypasses gate 3 but not gate 1. The runner must satisfy gate 1 (filled-in overview docs and `.ai-framework.json`) or use headless-specific role prompts. Decide in step 0.3 |
| F9 | Global `opencode.json` ends with `"*": "ask"`, which overrides the git allows and denies before it; a headless agent inheriting it cannot branch, commit or push | verified | Move the catch-all first when permissions are redefined (step 1.9). Evidence in `tests/bench/git-permissions-evidence.md` |
| F10 | Windows: the opencode shim goes through `cmd.exe`; quotes, pipes, braces in arguments break | verified | Plain-text task messages; pass artifacts as files; avoid long argv |
| F11 | `opencode run` loads skills from `~/.claude/skills`, adding about 20k cached tokens per run | verified | Part of per-run cost; account for it in comparisons |
| F12 | Spike results: model swap works; policy rejects before any model call; reports valid in 31/31 completed runs; 0% verdict flips on easy benchmark cases | verified | Architecture claim proven for the reviewer on easy cases |
| F13 | In headless runs an `ask` rule is auto-rejected (`permission requested ... auto-rejecting`), so `ask` behaves like `deny` | verified | Anything that needs a human can stay `ask` in headless runs and fails safe |
| F14 | The pre-push `branch_protection` check fails open: without `origin/HEAD` or `protectedBranches` in `.ai-framework.json` it warns and allows a push to `main`; the verify gate also skips when `.ai-framework.json` is missing | verified | Step 3A: read an explicit versioned list, fail closed, and fail the headless run when `.ai-framework.json` is missing. Server-side branch protection stays required |
| F15 | `deny` on `edit`, `write` and `task` removes those tools from the model's tool list instead of returning a permission error | verified | Record it as tool unavailable in evidence; the working-tree check still decides |
| F16 | The global config under `~/.config/opencode/` links into the framework repo (`opencode.json`, `AGENTS.md`, `agents`, `commands`, `hooks`, `scripts`, `skills`) | verified | A `git pull` on `main` changes live behavior for all projects. Test config changes in a throwaway setup before merging step 1.9 |
| U1 | `--session` can be used for retry | unverified | Do not rely on it in `report.py` |
| U2 | `bash: "*": deny` in a derived agent is parsed exactly as assumed | verified | Step 0.5 evidence |
| U3 | Cause of one failed GPT benchmark run | unverified | Step 2.4 |

## 3. Target folder structure

```text
ai-framework/
├── agents/                       # Phase 4: generated from roles/ + profile; never edited by hand afterwards
├── roles/                        # NEW: model-agnostic role definitions
│   ├── reviewer.json             # name, access intent (e.g. read-only), output contract
│   ├── reviewer.prompt.md
│   ├── qa.json / qa.prompt.md
│   └── ...
├── execution/                    # NEW
│   ├── policy.json               # { "models": {...}, "constraints": { "independence": [...], "protected_paths": [...] } }
│   ├── profiles/
│   │   ├── default.json          # role -> model routing
│   │   └── bench-*.json          # benchmark profiles
│   └── schemas/                  # the contracts between stages (role, profile, policy, review-report, qa-report, run-record)
├── adws/                         # NEW: thin runner (OpenCode only)
│   ├── runner.py                 # orchestrates one role run
│   ├── resolve.py                # policy filter, constraints, live-model check, fallback
│   ├── opencode_adapter.py       # access -> deny rules, derive agent file, run headless, parse events
│   ├── report.py                 # envelope parse/validate, retry, success levels
│   ├── record.py                 # RunRecord (JSONL)
│   └── pipeline_review_qa.py     # Phase 3C: throwaway experiment (MAX_FIX_LOOPS=3)
├── verification/                 # NEW: deterministic facts
│   ├── checks/                   # branch_protection, dependency_change, protected_paths, diff_size, build, tests, format, ...
│   ├── gates/                    # compose checks: pre_push, post_review
│   └── run.py
├── hooks/                        # existing; become thin entrypoints calling verification/
├── tools/
│   ├── validate_framework.py     # renamed from validate_agents.py (wrapper kept for transition)
│   └── lib/
│       ├── frontmatter.py        # strict parse
│       └── opencode_models.py    # provider-specific discovery (isolated here)
├── tests/
│   ├── fixtures/                 # valid + intentionally invalid
│   ├── test_*.py                 # unittest
│   └── bench/                    # baseline.md, permissions-evidence.md, bench.py, bench_cases.py, baseline profile
├── docs/
│   ├── transition-plan.md        # this file
│   └── decisions/
│       ├── DEC-011-...md         # Status: Superseded by DEC-016
│       ├── DEC-013, DEC-014      # unchanged
│       ├── DEC-015-deterministic-verification.md
│       ├── DEC-016-role-profile-policy.md
│       ├── MODEL-ASSIGNMENT-MATRIX.md  # Phase 4: generated from policy + profile
│       └── evaluations/          # one file per experimental model that gets promoted
├── skills/ commands/ instructions/ scripts/   # unchanged; skills stay runtime-agnostic
├── git-template/                 # generated by setup.py (unchanged mechanism)
└── setup.py                      # small additions only (run generator, link adws if needed)
```

Source of truth:

| Information | Source of truth |
|---|---|
| Role responsibility, prompt | `roles/*.json`, `roles/*.prompt.md` |
| Role access intent (for example `read-only`) | `roles/*.json` |
| Concrete OpenCode permissions | Derived by `opencode_adapter.py`; generated into `agents/*.md` in Phase 4 |
| Which model runs a role | `execution/profiles/` |
| Which models are legal, families, experimental status | `execution/policy.json` (`models`) |
| Independence rules, protected paths | `execution/policy.json` (`constraints`) |
| Contracts between stages | `execution/schemas/` |
| Workflow definition | The Phase 3C hardcoded pipeline (experiment only) |
| Deterministic rules and gates | `verification/` |
| Runtime invocation | `adws/opencode_adapter.py` |
| Evidence of what ran | `adws/runs/*.jsonl` |
| Why decisions were made | `docs/decisions/` |
| Human-readable model matrix | Generated `MODEL-ASSIGNMENT-MATRIX.md` |

## 4. Phases

Rules for every phase:
- Each commit is atomic and independently verifiable.
- Do not start a step before the previous step's test passes. If a test fails, fix or revert, never stack.
- No step deletes anything until Phase 4.
- Check the commit-msg hook format before the first commit of a phase.
- Merge at phase exit through a pull request (see "Working method").

### Phase 0: baseline, inventory and permission evidence (1-2 days)

Do 0.5 and 0.6 first. They test the two assumptions the architecture rests on. If either fails, stop and rethink Phase 2 before writing any code.

| Step | Do | Test |
|---|---|---|
| 0.1 | Create the Phase 0 branch and worktree | branch exists, `git worktree list` shows two folders (done) |
| 0.5 | Negative permission test. In a throwaway repo, run a derived read-only reviewer and ask it to: edit a file, write a new file, delegate through `task`, and run a shell command that writes. Record results in `tests/bench/permissions-evidence.md`; update the F4, F5 and U2 statuses | `git status --porcelain` is empty afterwards (`git diff --exit-code` alone misses new untracked files) |
| 0.6 | Git permission tests in a throwaway repo with a local bare remote (`git init --bare remote.git`), using the rule block from section 6 with the catch-all first: (1) branch and commit with no prompt, (2) push a feature branch with no prompt, (3) `git push origin main` is denied, and `git push origin HEAD:main` is stopped by the hook or noted as a gap, (4) `npm install lodash` prompts | all four behave as expected; settles decision #3 and the F9 status |
| 0.2 | Record 3-5 real past tasks on the current flow: outcome, review iterations (and cause: implementation / review / verification / environment / unclear requirement), time, tokens, what gatekeeper caught or missed | `tests/bench/baseline.md` exists, no empty fields ("unknown" allowed) |
| 0.3 | Inventory files not yet reviewed: `hooks/*`, `agents/gatekeeper.md`, `.ai-framework.json`, `tools/validate_agents.py` (including the 16 cross-family edges), `main` of `setup.py`, global `AGENTS.md`, `opencode.json` | inventory note lists each file with KEEP / MOVE / SPLIT / REPLACE / REMOVE |
| 0.4 | Draft the definition of "parity" (below) | draft committed; finalized as part of DEC-015 |

**Parity.** Same verification results and no regression in baseline outcome. Same model, same prompt count and same reasoning are not required.

| Class | Metrics | Role in decisions |
|---|---|---|
| Hard requirement | Correctness and verification results, reliability (schema validity, no policy or permission violations) | Must hold |
| Optimization | Cost, latency | Trade-offs allowed if outcome and verification hold |
| Diagnostic | Review iterations | Informs, does not decide |

Exit criterion: 0.5 and 0.6 pass (or Phase 2 is re-planned), and 0.2 to 0.4 are committed.

### Phase 1: harden the current framework (3-5 days, no behavior change for users except 1.9)

| Step | Do | Test |
|---|---|---|
| 1.1 | DEC-015 (deterministic verification principle: anything checkable in code is checked in code, LLMs judge) and DEC-016 (role / profile / policy separation; supersedes DEC-011's ownership model). DEC-016 also states that `execution/schemas/` are the contracts between stages and holds the artifact ownership table (section 5.2). Do not reuse the DEC-014 number | `grep -rn "DEC-016" .` resolves; current validator still passes |
| 1.2 | `unittest` harness and fixtures dir; first test runs the current validator on the real repo | `python -m unittest` green |
| 1.3 | Strict frontmatter parser in `tools/lib/frontmatter.py`. Known case: `code-reviewer.md` has a double-quoted `external_directory` path with backslashes, which is not valid YAML escaping | the validator flags that line (fixture) and the real file is fixed |
| 1.4 | Live model check via `tools/lib/opencode_models.py` (`opencode models`), isolated from the core validator | fixture: a model id `github-copilot/nope` fails naming agent and id |
| 1.5 | Read-only rule: any agent with `edit: deny` must also deny `write` and `task`. Fix the real agents | fixture fails; real agents pass after fix |
| 1.6 | `execution/policy.json` as data, grouped into `models` and `constraints`. Per model: `family` (`claude`, `gpt`, `gemini`; independent of provider, so `github-copilot/claude-sonnet-5` and `anthropic/claude-sonnet-5` are both `claude`), `status` (approved / experimental), `evaluation` path for promoted ones. Independence edges move from code into `constraints` | validator reads policy; DEC-014 fixtures (same model for planner and reviewer, experimental without evaluation) both fail |
| 1.7 | Rename to `validate_framework.py`, keep `validate_agents.py` as a wrapper | both entry points pass |
| 1.8 | Lint: framework-owned role and verification files (`roles/`, `verification/`, `execution/schemas/`) must not contain concrete model ids or provider names. Match ids (`claude-`, `gpt-`, `codex`, `o1`/`o3`-style, `gemini-`, and provider prefixes such as `anthropic/`, `github-copilot/`), not prose mentions such as "GPT models may..." | fixture with a model id fails; fixture with a prose mention passes |
| 1.9 | Apply the git and dependency permission rules from section 6 to the global `opencode.json` (catch-all first) and add the human-in-the-loop rules to `AGENTS.md`. The global `opencode.json` and `AGENTS.md` are links into this repo (F16), so edit the repo copies and test them in a throwaway setup before merging. Move the catch-all first and tighten patterns such as `git push*main*` | rerun the 0.6 tests against the real config; plus: on a `feat/x` branch, an unrelated request makes the agent ask "same branch or new one?" |

Exit criterion: validator rejects all three DEC-014 incident types. This phase is valuable even if everything after it is abandoned. Merge to `main` at exit.

### Phase 2: reviewer runner inside the repo (3-4 days), decision gate

| Step | Do | Test |
|---|---|---|
| 2.1 | Move the spike into `adws/`, `roles/reviewer.*`, `execution/profiles/`. `roles/reviewer.json` carries `access: read-only`; the adapter translates it into OpenCode deny rules; the validator checks the derived output. Split `runner.py` into `resolve.py`, `opencode_adapter.py`, `report.py`, `record.py` | offline unit tests: resolve rejections, event parsing, report validation, fallback warning caught, access-to-deny translation |
| 2.2 | Implement the three success levels (section 5.3) and the minimum `RunRecord` fields (section 5.4). On failure, records include the stderr tail and event tail | a forced failure produces a readable error; a run with "I couldn't complete the review" is execution success but not artifact success |
| 2.3 | Benchmark rework: replace the debatable `zero-division` fixture, add 4-6 harder cases (subtle logic error, bug hidden behind a passing test, cross-file context), tighten detection regexes, add a `baseline` profile that runs the real `code-reviewer` prompt in primary mode | fixtures build; offline summary works |
| 2.4 | Investigate the failed GPT benchmark run (error not yet seen) | cause identified, handled or documented; U3 resolved |
| 2.5 | Live benchmark, at least 3 repeats per model per case, with at least one model from each family (Claude, GPT, Gemini) | see gate below |

**Decision gate (end of Phase 2).** Proceed only if all hard requirements hold. Otherwise stop at Phase 1 plus a single config file for models.

Hard requirements:
- Report schema validity at or near 100%.
- No policy violations and no permission violations.
- A model swap changes only the profile, for all three families.
- Deterministic gates remain deterministic.

Directional metrics (inform the decision, no fixed threshold): bug recall versus the baseline reviewer, false positives on clean diffs, verdict stability on identical diffs, latency, tokens, cost. Three repeats per case is a small sample, so read these as direction, not as thresholds.

Also check the acceptance criteria in section 7 at this gate.

### Phase 3A: deterministic verification (about 1 week)

| Step | Do | Test |
|---|---|---|
| 3A.1 | Classify every gatekeeper checklist item as deterministic or judgment (table in DEC-015) | every item labeled |
| 3A.2 | `verification/checks/*` (one file per fact) and `verification/gates/*` (compose checks). Includes `branch_protection` (explicit protected-branch list, fails closed when it cannot decide), `dependency_change` (flags diffs to `package.json`, `package-lock.json`, `yarn.lock`, `pnpm-lock.yaml`, `pom.xml`, `build.gradle*`; blocks the push unless the commit carries a `Dependency-Approved:` trailer) and `protected_paths` (before/after tree diff against `constraints.protected_paths`). `hooks/` become thin entrypoints calling `verification/run.py`; keep the hard-link mechanism in `add_git_template` and add the new files to its tuple | per check: one passing and one failing fixture; a manifest change without the trailer is blocked at push; fresh clone blocks a bad push on Windows |
| 3A.3 | Hook interpreter risk: hooks written in Python need `python3`/`python` resolvable from Git Bash. `setup.py` adds an "action required" entry if not | tested on this machine |
| 3A.4 | Trim `gatekeeper` to judgment-only items; replay the baseline tasks | no more misses than baseline; then decide whether the tier can drop |

**Gate 3A.** Fresh-clone test in a throwaway clone passes, and gatekeeper replay shows no regression. Otherwise stop here: 3A is valuable without 3B and 3C.

### Phase 3B: additional roles (3-5 days)

| Step | Do | Test |
|---|---|---|
| 3B.1 | `qa` role through the same mechanism (QAReport envelope) | passes the model-swap test across families |
| 3B.2 | `plan-reviewer` role | passes the model-swap test across families |

**Gate 3B.** Proceed to 3C only if both roles pass the swap test and the Phase 2 results still hold.

### Phase 3C: pipeline experiment (3-5 days, throwaway)

This is an experiment to learn whether multi-role execution is worth building. It is not a workflow engine. Keep the pipeline hardcoded and local, with no configuration-driven stages.

| Step | Do | Test |
|---|---|---|
| 3C.1 | Permissions for implementation roles in the runner: write-allowed gate using `constraints.protected_paths` (decision #1) | only allowed paths change; protected paths (`hooks/`, `agents/`, `.ai-framework.json`, `execution/policy.json`, `setup.py`) never change |
| 3C.2 | `pipeline_review_qa.py`: reviewer -> qa -> quality commands (argv lists from `.ai-framework.json`, exit code, last 50 lines) -> gates; `MAX_FIX_LOOPS = 3`; stop reason is readable and no LLM decides to stop | happy path accepted; injected failing test loops then stops at 3 |

**Outcome (recorded in DEC-015):** keep as is, replace with a declarative definition, or remove, based on evidence.

### Phase 4: single source of truth and migration (3-5 days)

| Step | Do | Test |
|---|---|---|
| 4.1 | Generator: `roles/` + profile -> `agents/*.md` frontmatter (model, mode `subagent` for interactive use, permissions derived from `access`). Header marks files as generated and "never edit by hand". Generated files stay committed so a fresh clone works even if generation fails. The runner still derives primary-mode agents at run time | validator fails on drift between generated and committed files |
| 4.2 | `setup.py` runs the generator; handle the Windows copy fallback (`OUT OF DATE` warning already exists) | fresh clone: setup, generate, validator green |
| 4.3 | `MODEL-ASSIGNMENT-MATRIX.md` generated from policy and profile; DEC-011 marked Superseded by DEC-016 | matrix equals generated output |
| 4.4 | Compatibility check (temporary): old frontmatter models equal profile-resolved models | zero differences, then remove the check |
| 4.5 | Soak: 5 real PRs on the new path; compare with baseline (escapes, retries, time, tokens) using the parity classes from 0.4 | verdict recorded in DEC-015: keep, extend, or revert; section 7 criteria re-checked |
| 4.6 | Bump `FRAMEWORK_VERSION`, `CHANGELOG.md`, update `docs/session-summary.md` | version consistent |
| 4.7 | Instruction entry points for each tool: check how Copilot, Codex and Gemini CLI load `AGENTS.md`; add thin pointer files where a tool uses its own filename (for example `GEMINI.md`) | each tool picks up the same instructions |
| 4.8 | Optional: `new-role <name>` scaffold command that creates the role files and a profile entry | a scaffolded role passes the validator |

Nothing is deleted before 4.5 passes. After it: remove hand-maintained model fields and obsolete matrix text.

## 5. Design rules

### 5.1 Role access intent vs runtime permissions
`roles/*.json` holds an intent such as `access: read-only`. The OpenCode adapter translates it into concrete deny rules (`edit`, `write`, `task`, and `bash` deny or a tight allow-list). The validator checks the derived output, not the intent alone.

### 5.2 Contracts and artifact ownership
`execution/schemas/` are the contracts between stages. Stages hand off through artifacts that validate against them, never through implicit agent context.

| Artifact | Owner |
|---|---|
| `review.json` | `reviewer` |
| `qa.json` | `qa` |
| Verification results | `verification/` |
| `RunRecord` | runner |

No stage modifies another stage's artifact.

### 5.3 Three success levels
| Level | Question | Decided by |
|---|---|---|
| Execution | Did OpenCode run to a normal stop? (`text` event + `reason: "stop"` + no `error` event) | adapter |
| Artifact | Is there a valid report that matches the schema? | `report.py` |
| Workflow | Do the report and the deterministic gates satisfy the requirements? | gates |

A response like "I couldn't complete the review" can pass the first level and must fail the second.

### 5.4 RunRecord minimum fields
`run_id`, `timestamp`, `role`, `profile`, `runtime`, `requested_model`, `resolved_model`, `policy_result`, `fallback`, `input_artifacts`, `output_artifacts`, `status` (per success level), `stop_reason`, `tokens`, `cost`, `duration_ms`, `verification`, `error`. These answer "why did this model actually run?"

### 5.5 Policy shape and families
`policy.json` is grouped into `models` and `constraints`. `family` is independent of provider: it names the model lineage (`claude`, `gpt`, `gemini`; Codex models are `gpt`). The cross-family independence rule compares families, not providers.

### 5.6 Protected paths
Protected paths are versioned data (`constraints.protected_paths`), enforced by comparing the working tree before and after a run. The check does not rely on what the agent reports.

### 5.7 Provider boundary
OpenCode-specific knowledge stays in `opencode_adapter.py`, the access-to-permission translation and `opencode_models.py`. The runner knows "the requested execution mode was not honored"; the adapter knows how OpenCode expresses that (F6). `roles/` and `verification/` contain no provider or runtime names.

### 5.8 Generated files
After Phase 4, `agents/*.md` and `MODEL-ASSIGNMENT-MATRIX.md` are never edited by hand. The validator detects drift.

## 6. Git and dependency permissions

**Allowed without approval:** create branches, add, commit, push feature branches, open draft PR/MR.
**Blocked or asked:** push to `main`/`master`, force push, non-draft PR, merge, mark ready.

Global `opencode.json` (catch-all first, because the last matching rule wins, F9):

```json
"bash": {
  "*": "ask",
  "git status*": "allow", "git diff*": "allow", "git log*": "allow",
  "git switch -c *": "allow", "git checkout -b *": "allow",
  "git add *": "allow", "git commit *": "allow",
  "git push -u origin *": "allow",
  "git push*--force*": "deny",
  "git push*main*": "deny", "git push*master*": "deny",
  "python scripts/open-draft-pr.py*": "allow",
  "gh pr create*": "ask", "gh pr merge*": "deny",
  "npm ci": "allow",
  "npm install *": "ask", "yarn add*": "ask", "pnpm add*": "ask",
  "mvn*versions:*": "ask"
}
```

Draft mode is guaranteed by the `pr-provider` script, not by pattern matching. Patterns cannot catch everything (`git push origin HEAD:main` slips past them), and they only protect OpenCode. The runtime-agnostic enforcement, which also covers Copilot, Codex and Gemini, is the `branch_protection` and `dependency_change` checks in the pre-push gate plus server-side branch protection on the remote.

**Human in the loop 1: third-party dependencies.**
- Interactive: package-manager commands are `ask`, so a real prompt appears.
- Backstop: the `dependency_change` check blocks the push unless the commit has a `Dependency-Approved:` trailer. Code cannot prove a human approved it, but the trailer makes it visible and reviewable.
- Headless runner: these commands are `deny`, and a manifest change fails the run.

**Human in the loop 2: new task on an existing branch.** This is a judgment call, so it lives in `AGENTS.md`, not code.
- On any non-main branch, when a request is not clearly a continuation, ask: same branch or new one?
- Record each branch's purpose with `git config branch.<name>.description "<task>"`, so the agent has something to compare against.
- Headless: the runner states the decision in the task message (F8), for example "work on the current branch" or "create a branch named X".

## 7. Acceptance criteria

Checked at the Phase 2 gate and again at 4.5. A phase that breaks one is a reason to stop or simplify, the same way a failed benchmark is.

- **Install and update stay simple.** A fresh clone reaches a green validator with no steps beyond today's (`git pull` + `python setup.py`).
- **A new role is cheap and safe.** It touches at most 3 files (`roles/x.json`, `roles/x.prompt.md`, a profile entry) and is caught by the validator if misconfigured.
- **Health check is one command.** `validate_framework.py` covers schemas, policy, permissions, the lint and generated-file drift; `python -m unittest` is the second.
- **No Claude-only assumption** in framework-owned files, and a reviewer run passes with one model per family (Claude, GPT, Gemini), changing only the profile.

## 8. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Headless agents stop at global `AGENTS.md` gates (F8) | A pre-approval sentence is not enough for the first-run gate. Satisfy the gate in the target repo, or use headless-specific role prompts (decided in step 0.3) |
| Silent subagent fallback (F6) | Adapter derives primary-mode files and fails on the warning |
| Permission leaks through delegation or tool-name variance (F5, F7) | Explicit denies, validator rule, step 0.5 evidence, tree-diff gate |
| Windows quirks (F10, symlink privileges, Git Bash Python) | Plain messages, files as artifacts, `setup.py` action-required entries, Git Bash for all commands |
| Maintenance burden of contracts, policy, runner | Keep the Phase 2 gate honest; stop at Phase 1 if there is no gain |
| Phase 3C grows into a workflow engine | Hardcoded and throwaway; outcome recorded in DEC-015; declarative definitions stay deferred |
| Noisy comparisons (3-5 tasks, non-deterministic models) | Treat results as directional; log failures, do not chase averages |
| Cost of skills loaded per run (F11) | Track in `RunRecord`; consider a leaner role prompt for headless runs |
| Pattern-based git rules miss bypasses | Pre-push gate and server-side branch protection are the real enforcement |
| Pre-push hook fails open (F14) | Explicit protected-branch list, fail closed, server-side branch protection |
| Broad deny patterns such as `git push*main*` also match unrelated branch names | Tighten the patterns in step 1.9 and retest |
| Tools differ in instruction file names (`AGENTS.md`, `GEMINI.md`) | Step 4.7 pointer files |
| Live install changes by accident while working | Worktree per phase; throwaway-clone test for 3A and 4 |

## 9. Decisions needed from you

1. **Which paths may implementation roles write, and what must always be protected?** The git permission rules are decided (section 6). The path list decides the 3C.1 write-allowed gate. Answer before Phase 2 ends.
2. **Hooks in Python.** Port `pre-commit`, `commit-msg`, `pre-push`, `build-verify.sh` to Python, or keep shell and call Python from them? Can wait until 3A.
3. **Global `opencode.json` ordering.** Move `"*": "ask"` to the top of the bash block so your git allows take effect? Settled by step 0.6: yes, move it first (F9 verified).
4. **Profile location.** Keep one default profile in the framework, or also support a per-project override such as `<project>/.ai-framework/execution-profile.json`? Can wait until Phase 4.
5. **Parity margin** for the Phase 2 gate (what difference from the baseline reviewer is acceptable on the directional metrics). Answer before Phase 2 ends.

## 10. What is not changing

`skills/`, `commands/`, `instructions/`, `scripts/`, the symlink and junction logic, the git-template hard-link mechanism, the cross-family validation intent, and all historical DECs.
