# ai-framework transition plan: role / profile / policy separation

Status: proposed, 2026-10-02. Based on the Stage 0 feasibility tests and the reviewer spike (see `handoff.md`).

## 1. Goal and scope

**Goal.** Separate three things that are currently fused in `agents/*.md` and `MODEL-ASSIGNMENT-MATRIX.md`:

| Concern | Today | Target |
|---|---|---|
| Role (responsibility, permissions, prompt) | `agents/*.md` | `roles/<role>.json` + `roles/<role>.prompt.md`, no model |
| Model selection | `model:` in agent frontmatter + matrix | `execution/profiles/*.json` |
| Constraints (allowed models, families, experimental status, independence) | matrix prose + `validate_agents.py` | `execution/policy.json`, enforced by code |
| Verification facts (build, tests, branch, diff) | partly `gatekeeper` (LLM) | `verification/checks` + `gates`, run by code |

**Why (evidence, not theory).** DEC-014 documents three incidents: the same model assigned to planner and plan-reviewer, an experimental model assigned without evaluation, and a gatekeeper tier decided by hand. All three are preventable by a validated profile plus policy. The spike proved a model swap needs only a profile change (reviewer GPT vs Claude, same role, runner and gates).

**Runtime.** OpenCode only. The IDE Copilot uses `skills/` and the pre-push hook but does not run agents.

**Language.** Python, stdlib only. This is the current implementation choice (matches `setup.py` and `tools/`), not an architectural principle.

**Repository.** Same repo, on a branch (for example `feat/execution-profiles`). A new repo would duplicate `setup.py`, symlinks, hooks and the DEC history.

### Deliberately deferred (revisit only on a concrete trigger)

| Deferred | Trigger to revisit |
|---|---|
| Second runtime / provider adapter | You actually need to run agents outside OpenCode |
| Capability-based routing and a capability catalog | Explicit mapping becomes painful across many roles |
| Workflow YAML replacing the orchestrator | Runner pipeline is stable and orchestrator duplication hurts |
| Visualizer / SQLite tracer | JSONL run records stop being enough |
| Provider factory, registry, executor abstractions | A second adapter exists |

## 2. Findings that drive the design (measured)

| # | Finding | Design consequence |
|---|---|---|
| F1 | Headless `opencode run --format json` emits clean JSONL; `step_finish` carries tokens and cost | `RunRecord` can log usage and cost |
| F2 | Exit code is 0 even when the agent did nothing (permission rejection, ask-then-stop) | Success = `text` event + `reason: "stop"` + no `error` event |
| F3 | Hard failure (bad model id) gives exit 1 and a generic `error` event | Validate model ids before running |
| F4 | Permissions are default-allow; the last matching rule wins (inferred from the rule dump) | Read-only roles need explicit `edit`, `write`, `task` deny, and `bash` deny or a tight allow-list; validator enforces |
| F5 | Delegation through `task` bypassed `write: deny` until `task: deny` was added | Deny `task` for read-only roles |
| F6 | `--agent X` on a `mode: subagent` agent silently falls back to the default agent (stderr warning only) | Runner derives primary-mode agent files; the warning is a hard failure |
| F7 | Tool names vary by model (`apply_patch` vs `edit`) | Gates inspect the working tree, not tool names |
| F8 | Global `AGENTS.md` makes agents create branches and ask for confirmation; headless cannot answer | Runner pre-approves in the prompt, or roles carry non-interactive instructions |
| F9 | Global `opencode.json` ends with `"*": "ask"`, which overrides earlier git allows | Move catch-all first when permissions are redefined |
| F10 | Windows: the opencode shim goes through `cmd.exe`; quotes, pipes, braces in arguments break | Plain-text task messages; pass artifacts as files; avoid long argv |
| F11 | `opencode run` loads skills from `~/.claude/skills`, adding about 20k cached tokens per run | Part of per-run cost; account for it in comparisons |
| F12 | Spike results: model swap works; policy rejects before any model call; reports valid in 31/31 completed runs; 0% verdict flips on benchmark cases | Architecture claim proven for the reviewer |

Unverified (do not rely on): `--session` for retry; that `bash: "*": deny` in a derived agent is parsed exactly as assumed; the cause of one failed GPT benchmark run.

## 3. Target folder structure

```text
ai-framework/
├── agents/                       # Phase 4: model in frontmatter becomes generated; body from roles/
├── roles/                        # NEW: model-agnostic role definitions
│   ├── reviewer.json
│   ├── reviewer.prompt.md
│   ├── qa.json / qa.prompt.md
│   └── ...
├── execution/                    # NEW
│   ├── policy.json               # allowed/blocked/experimental models, families, independence edges
│   ├── profiles/
│   │   ├── default.json          # role -> model routing, constraints
│   │   └── bench-*.json          # benchmark profiles
│   └── schemas/                  # JSON Schema exports of the contracts (documentation + validation)
├── adws/                         # NEW: thin runner (OpenCode only)
│   ├── runner.py                 # orchestrates one role run
│   ├── resolve.py                # policy filter, constraints, live-model check, fallback
│   ├── opencode_adapter.py       # derive agent file, run headless, parse events
│   ├── report.py                 # envelope parse/validate, retry
│   ├── record.py                 # RunRecord (JSONL)
│   └── pipeline_review_qa.py     # Phase 3: reviewer -> qa -> quality -> gates (MAX_FIX_LOOPS=3)
├── verification/                 # NEW: deterministic facts
│   ├── checks/                   # branch_protection, diff_size, build, tests, format, ...
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
│   └── bench/                    # bench.py, bench_cases.py, baseline profile
├── docs/decisions/
│   ├── DEC-011-...md             # Status: Superseded by DEC-016
│   ├── DEC-013, DEC-014          # unchanged
│   ├── DEC-015-deterministic-verification.md
│   ├── DEC-016-role-profile-policy.md
│   ├── MODEL-ASSIGNMENT-MATRIX.md  # Phase 4: generated from policy + profile
│   └── evaluations/              # one file per experimental model that gets promoted
├── skills/ commands/ instructions/ scripts/   # unchanged; skills stay runtime-agnostic
├── git-template/                 # generated by setup.py (unchanged mechanism)
└── setup.py                      # small additions only (run generator, link adws if needed)
```

Source-of-truth table:

| Information | Source of truth |
|---|---|
| Role responsibility, prompt, permissions | `roles/` |
| Which model runs a role | `execution/profiles/` |
| What models may be used, families, experimental status | `execution/policy.json` |
| Deterministic rules | `verification/` |
| Why decisions were made | `docs/decisions/` |
| Evidence of what ran | `adws/runs/*.jsonl` |

## 4. Phases

Rules for every phase:
- Each commit is atomic and independently verifiable (not "one step = one commit" at any size).
- Do not start a step before the previous step's test passes. If a test fails, fix or revert, never stack.
- No step deletes anything until Phase 4.

### Phase 0: baseline and inventory (1-2 days)

| Step | Do | Test |
|---|---|---|
| 0.1 | Create branch `feat/execution-profiles` | branch exists |
| 0.2 | Record 3-5 real past tasks on the current flow: outcome, review iterations (and cause: implementation / review / verification / environment / unclear requirement), time, tokens, what gatekeeper caught or missed | `tests/bench/baseline.md` exists |
| 0.3 | Inventory files not yet reviewed: `hooks/*`, `agents/gatekeeper.md`, `.ai-framework.json`, `tools/validate_agents.py` (including the 16 cross-family edges), `main` of `setup.py`, global `AGENTS.md`, `opencode.json` | inventory note lists each file with KEEP / MOVE / SPLIT / REPLACE / REMOVE |
| 0.4 | Define "parity": same verification results and no regression in baseline metrics (outcome, iterations, cost). Same model, same prompt count, same reasoning are not required | definition committed in DEC-015 |

### Phase 1: harden the current framework (3-5 days, no behavior change for users)

| Step | Do | Test |
|---|---|---|
| 1.1 | DEC-015 (deterministic verification principle: anything checkable in code is checked in code, LLMs judge) and DEC-016 (role / profile / policy separation; supersedes DEC-011's ownership model). Do not reuse the DEC-014 number | `grep -rn "DEC-016" .` resolves; current validator still passes |
| 1.2 | `unittest` harness and fixtures dir; first test runs the current validator on the real repo | `python -m unittest` green |
| 1.3 | Strict frontmatter parser in `tools/lib/frontmatter.py`. Known case: `code-reviewer.md` has a double-quoted `external_directory` path with backslashes, which is not valid YAML escaping | the validator flags that line (fixture) and the real file is fixed |
| 1.4 | Live model check via `tools/lib/opencode_models.py` (`opencode models`), isolated from the core validator | fixture: a model id `github-copilot/nope` fails naming agent and id |
| 1.5 | Read-only rule: any agent with `edit: deny` must also deny `write` and `task`. Fix the real agents | fixture fails; real agents pass after fix |
| 1.6 | `execution/policy.json` as data: per model `family`, `status` (approved / experimental), `evaluation` path for promoted ones; independence edges moved from code into data | validator reads policy; DEC-014 fixtures (same model for planner and reviewer, experimental without evaluation) both fail |
| 1.7 | Rename to `validate_framework.py`, keep `validate_agents.py` as a wrapper | both entry points pass |
| 1.8 | Lint: no model strings (`claude-`, `gpt-`, `gemini-` and similar) inside `roles/` and later `verification/` | fixture with a model string fails |

Exit criterion: validator rejects all three DEC-014 incident types. This phase is valuable even if everything after it is abandoned.

### Phase 2: reviewer runner inside the repo (3-4 days), decision gate

| Step | Do | Test |
|---|---|---|
| 2.1 | Move the spike into `adws/`, `roles/reviewer.*`, `execution/profiles/`. Split `runner.py` into `resolve.py`, `opencode_adapter.py`, `report.py`, `record.py` | offline unit tests: resolve rejections, event parsing, report validation, fallback warning caught |
| 2.2 | Run records include findings and, on failure, the stderr tail and event tail | a forced failure produces a readable error |
| 2.3 | Benchmark rework: replace the debatable `zero-division` fixture, add 4-6 harder cases (subtle logic error, bug hidden behind a passing test, cross-file context), tighten detection regexes, add a `baseline` profile that runs the real `code-reviewer` prompt in primary mode | fixtures build; offline summary works |
| 2.4 | Investigate the failed GPT benchmark run (error not yet seen) | cause identified, handled or documented |
| 2.5 | Live benchmark, at least 3 repeats per model per case | see gate below |

**Decision gate (end of Phase 2).** Proceed only if all hold, otherwise stop at Phase 1 plus a single config file for models:
- Reviewer via profile is within an agreed margin of the baseline reviewer on bug recall, with no increase in false positives on clean diffs.
- Verdict flips on identical diffs stay low (target under 30%, observed 0% on easy cases).
- Report schema validity stays at or near 100%.
- A model swap still changes only the profile.

### Phase 3: deterministic gates and the review/QA pipeline (1-2 weeks)

| Step | Do | Test |
|---|---|---|
| 3.1 | Classify every gatekeeper checklist item as deterministic or judgment (table in DEC-015) | every item labeled |
| 3.2 | `verification/checks/*` (one file per fact) and `verification/gates/*` (compose checks). `hooks/` become thin entrypoints calling `verification/run.py`; keep hard-link mechanism in `add_git_template` and add the new files to its tuple | per check: one passing and one failing fixture; fresh clone blocks a bad push on Windows |
| 3.3 | Hook interpreter risk: hooks written in Python need `python3`/`python` resolvable from Git Bash. `setup.py` adds an "action required" entry if not | tested on this machine |
| 3.4 | Trim `gatekeeper` to judgment-only items; replay the baseline tasks | no more misses than baseline; then decide whether the tier can drop |
| 3.5 | Additional roles via the same mechanism: `qa` first (QAReport envelope), then `plan-reviewer` | each role passes the model-swap test |
| 3.6 | `pipeline_review_qa.py`: reviewer -> qa -> quality commands (argv lists from `.ai-framework.json`, exit code, last 50 lines) -> gates; `MAX_FIX_LOOPS = 3`; stop reason is readable and no LLM decides to stop | happy path accepted; injected failing test loops then stops at 3 |
| 3.7 | Permissions for implementation roles in the runner: decision needed (see section 6) | write-allowed gate: only allowed paths change; protected paths (`hooks/`, `agents/`, `.ai-framework.json`) never change |

### Phase 4: single source of truth and migration (3-5 days)

| Step | Do | Test |
|---|---|---|
| 4.1 | Generator: `roles/` + profile -> `agents/*.md` frontmatter (model, mode `subagent` for interactive use). Header marks files as generated. Runner still derives primary-mode agents at run time | validator fails on drift between generated and committed files |
| 4.2 | `setup.py` runs the generator; handle the Windows copy fallback (`OUT OF DATE` warning already exists) | fresh clone: setup, generate, validator green |
| 4.3 | `MODEL-ASSIGNMENT-MATRIX.md` generated from policy and profile; DEC-011 marked Superseded by DEC-016 | matrix equals generated output |
| 4.4 | Compatibility check (temporary): old frontmatter models equal profile-resolved models | zero differences, then remove the check |
| 4.5 | Soak: 5 real PRs on the new path; compare with baseline (escapes, retries, time, tokens) | verdict recorded in DEC-015: keep, extend, or revert |
| 4.6 | Bump `FRAMEWORK_VERSION`, `CHANGELOG.md`, update `docs/session-summary.md` | version consistent |

Nothing is deleted before 4.5 passes. After it: remove hand-maintained model fields and obsolete matrix text.

## 5. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Headless agents stop to ask for confirmation (F8) | Pre-approval text in the task message; or role prompts without the interactive workflow |
| Silent subagent fallback (F6) | Runner derives primary-mode files and fails on the warning |
| Permission leaks through delegation or tool-name variance (F5, F7) | Explicit denies, validator rule, tree-diff gate |
| Windows quirks (F10, symlink privileges, Git Bash Python) | Plain messages, files as artifacts, `setup.py` action-required entries |
| Maintenance burden of contracts, policy, runner | Keep Phase 2 gate honest; stop at Phase 1 if there is no gain |
| Noisy comparisons (3-5 tasks, non-deterministic models) | Treat results as directional; log failures, do not chase averages |
| Cost of skills loaded per run (F11) | Track in `RunRecord`; consider a leaner role prompt for headless runs |

## 6. Decisions needed from you

1. **Permissions for implementation roles in the runner.** You are loosening git permissions (auto-push, draft PRs). Which paths may implementers write, and what must always be protected? This decides the write-allowed gate.
2. **Hooks in Python.** Port `pre-commit`, `commit-msg`, `pre-push`, `build-verify.sh` to Python, or keep shell and call Python from them?
3. **Global `opencode.json` permissions.** Move `"*": "ask"` to the top of the bash block so your git allows take effect (inferred, to be tested)?
4. **Profile location.** Keep one default profile in the framework, or also support a per-project override such as `<project>/.ai-framework/execution-profile.json`?
5. **Parity margin** for the Phase 2 gate (what difference from the baseline reviewer is acceptable).

## 7. What is not changing

`skills/`, `commands/`, `instructions/`, `scripts/`, the symlink and junction logic, the git-template hard-link mechanism, the cross-family validation intent, and all historical DECs.
