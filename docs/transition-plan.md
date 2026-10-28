# ai-framework transition plan: role / profile / policy separation

Status: proposed 2026-10-02, revised 2026-10-03 after review, revised 2026-10-18 (model routing: decisions #4 and #8), revised 2026-10-21 (Phase 1b closed in code). Based on the Stage 0 feasibility tests (see `handoff.md`) and on the routing experiments E1 to E4 (F32 to F36).

Note (2026-10-18): the reviewer spike mentioned in this plan is not in the repository. Phase 2 writes the runner from scratch and re-tests F12.

## 1. Goal and scope

**Goal.** Separate three things that are currently fused in `agents/*.md` and `MODEL-ASSIGNMENT-MATRIX.md`:

| Concern | Today | Target |
|---|---|---|
| Role (responsibility, prompt, permissions) | `agents/*.md` | `agents/*.md` without a `model:` line (no separate `roles/` layer, decision #8) |
| Model selection | `model:` in agent frontmatter + matrix | `execution/profiles/default.json` only, rendered into a generated routing file that is linked as `~/.config/opencode/config.json` |
| Constraints (allowed models, families, experimental status, independence, protected paths) | matrix prose + `validate_agents.py` | `execution/policy.json`, enforced by code |
| Verification facts (build, tests, branch, diff, dependency changes) | partly `gatekeeper` (LLM) | `execution/verification/checks` + `gates`, run by code |

**Principle.** LLMs make judgments; code determines facts.

**Why (evidence, not theory).** DEC-014 documents three incidents: the same model assigned to planner and plan-reviewer, an experimental model assigned without evaluation, and a gatekeeper tier decided by hand. All three are preventable by a validated profile plus policy. An earlier spike reported that a model swap needs only a profile change (reviewer GPT vs Claude, same role, runner and gates); its code is not in the repository, so Phase 2 reproduces it (F12). Experiments E1 to E4 (F32 to F36) showed how OpenCode really resolves a model, and decision #8 follows from them.

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
  | 1b | `feat/phase-1b-model-routing` |
  | 2 | `feat/phase-2-reviewer-runner` |
  | 3A | `feat/phase-3a-verification` |
  | 3B | `feat/phase-3b-roles` |
  | 3C | `feat/phase-3c-pipeline-experiment` |
  | 4 | `chore/phase-4-soak` |
- **Repo hooks:** direct commits to `main` are blocked, and branch names need a prefix (`feat/ fix/ chore/ refactor/ docs/ hotfix/ release/`). Merging is done through a GitHub pull request, not a local merge.
- **Merge rule:** `main` is what is installed, so only merge what you would be comfortable having live today. Merge at phase exit, when the phase's exit test passes.
- **Phases that change live behavior (1b model routing, 3A hooks):** verify in a throwaway clone with a fresh `setup.py` run before opening the PR.
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
| F8 | Global `AGENTS.md` gates stop headless agents: (1) a first-run gate when `docs/project-overview/stack.md` is missing or only a heading, (2) the agent creates a branch on its own, (3) the agent asks to confirm its plan before writing | verified | A pre-approval sentence in the task message bypasses gate 3 but not gate 1. The runner must satisfy gate 1 (filled-in overview docs and `.ai-framework.json`). Decided in step 0.3: the runner runs a preflight check in code and fails closed; no headless-specific `AGENTS.md` (`docs/inventory.md`, section 4) |
| F9 | Global `opencode.json` ends with `"*": "ask"`, which overrides the git allows and denies before it; a headless agent inheriting it cannot branch, commit or push | verified | Move the catch-all first when permissions are redefined (step 1.9). Evidence in `tests/bench/git-permissions-evidence.md` |
| F10 | Windows: the opencode shim goes through `cmd.exe`; quotes, pipes, braces in arguments break | verified | Plain-text task messages; pass artifacts as files; avoid long argv |
| F11 | `opencode run` loads skills from `~/.claude/skills`, adding about 20k cached tokens per run | verified | Part of per-run cost; account for it in comparisons |
| F12 | Spike results: model swap works; policy rejects before any model call; reports valid in 31/31 completed runs; 0% verdict flips on easy benchmark cases | verified (earlier run; code not in the repo) | Evidence, not proof: Phase 2 reproduces it. Architecture claim for the reviewer on easy cases |
| F13 | In headless runs an `ask` rule is auto-rejected (`permission requested ... auto-rejecting`), so `ask` behaves like `deny` | verified | Anything that needs a human can stay `ask` in headless runs and fails safe |
| F14 | The pre-push `branch_protection` check fails open: without `origin/HEAD` or `protectedBranches` in `.ai-framework.json` it warns and allows a push to `main`; the verify gate also skips when `.ai-framework.json` is missing | verified | Step 3A: read an explicit versioned list, fail closed, and fail the headless run when `.ai-framework.json` is missing. Server-side branch protection stays required |
| F15 | `deny` on `edit`, `write` and `task` removes those tools from the model's tool list instead of returning a permission error | verified | Record it as tool unavailable in evidence; the working-tree check still decides |
| F16 | The global config under `~/.config/opencode/` links into the framework repo (`opencode.json`, `AGENTS.md`, `agents`, `commands`, `hooks`, `scripts`, `skills`) | verified | A `git pull` on `main` changes live behavior for all projects. Test config changes in a throwaway setup before merging step 1.9 |
| F17 | `opencode agent list` reads agents through the global links, so it shows the files in the main folder and ignores edits in a worktree. Copying the agents into a throwaway project's `.opencode/agents/` shows the edited versions. After step 1.5, the edited `architect` showed a `task` rule with `deny` and pattern `*` (OpenCode reads the scalar form), while the live list showed none | verified | Test agent changes in a throwaway project before trusting them; use it in steps 1b.5 and 2.1 |
| F18 | A double-quoted Windows path in agent frontmatter (`"D:\ai-framework\...\*"`) was not registered as written: the live list for `code-reviewer` had no rule for the `linting-tools\references` folder, and the single-quoted version registers it. The loss is silent | verified | Keep the strict escape check (step 1.3). Compare derived agents against `opencode agent list` in tests where possible |
| F19 | Setting `XDG_CONFIG_HOME` to a folder that holds `opencode/opencode.json` makes OpenCode read that file as its global config, so a global-config change can be tested without touching the live links. A probe rule (`git tag xdg-probe*`) shows the override is active. With the catch-all first, `git checkout -b`, `git switch -c` and the probe ran; `git commit`, `git push`, `git branch -D` and `gh pr ready` were denied by rule; `npm install` was auto-rejected | verified | Test every global-config change this way before merging (steps 1.9, 1b.5 and 1b.6) |
| F20 | An agent's own `"*"` rule comes after the global rules in the merged order, so it overrides every global rule before it: the global denies for `gh pr ready*`, `git branch -D *` and `git commit*--no-verify*` do not protect an agent whose block starts with `"*": ask`, such as the orchestrator | verified | Agents that can commit repeat the denies in their own block; the validator enforces it (`lint_commit_agents`, DEC-017) |
| F21 | A "stay on this branch" option was offered on a branch that held another task's commits | verified | Fixed: the branch question uses the ahead-of-base count |
| F22 | Implementer subagents asked the branch question themselves | verified | Fixed in `AGENTS.md` Check 2: only the orchestrator asks |
| F23 | The reviewer needed `python -m lizard` and was denied | verified | Fixed: allow added |
| F24 | Read-only git commands were denied for some agents | verified | Fixed: `git-context` allowed for the agents that fall back to ask |
| F25 | `$env:USERPROFILE` expands to nothing in the OpenCode bash tool | verified | Agents call scripts with `$HOME`; the validator rejects `$env:` |
| F26 | The jscpd report folder got committed | verified | Fixed: ignored |
| F27 | The orchestrator edited files through `node -e` via an approved prompt | verified | Fixed: its bash fallback is `deny`; lint for every agent that can commit |
| F28 | A subagent's own `"*": ask` overrode the `git-context` allow | verified | Fixed + lint (same mechanism as F20) |
| F29 | jscpd analyzed 0 files on tiny inputs, so every earlier PASS was empty | verified | Fixed: the result is `PARTIAL` or `NOT_ANALYZED`, never PASS. A live example of why execution success is not workflow success (section 5.3) |
| F30 | `qa` prompted on `node --test` | verified | Fixed + lint |
| F31 | Whether an allow pattern such as `node --test *` also matches chained commands is not known | unverified | Test in a headless run (F13) before relying on any allow pattern for security |
| F32 | An agent file's `model:` line beats an `agent.<name>.model` entry in `opencode.json` (`opencode debug agent` printed the frontmatter model) | verified | A leftover `model:` line silently defeats routing. The validator rejects `model:` lines in agent files |
| F33 | An `agent.<name>.model` entry applies to a markdown agent that has no `model:` line, in `opencode debug agent` and at run time (the child session recorded the routed model) | verified | The profile can route models through config alone |
| F34 | A subagent with no model anywhere runs on its caller's model (caller on haiku gave haiku, caller on gpt-5.4-mini gave gpt-5.4-mini) | verified | A role missing from the profile silently shares the caller's model: the DEC-014 incident. The validator requires an entry for every agent and checks the resolved model. A task result carries `metadata.model` and `sessionId` per child, so the runner can compare it with the profile |
| F35 | Config precedence, highest first: agent frontmatter, `OPENCODE_CONFIG` file, project `opencode.json`, global `opencode.json`, global `config.json`. `OPENCODE_CONFIG` against the project file was not tested | verified | Anything above `config.json` silently overrides the routing; a project `opencode.json` can re-route any agent (decision #4) |
| F36 | A file named `config.json` in the global config dir is read alongside `opencode.json` (permissions from one, model from the other); a file named `routing.json` was ignored; no deprecation warning in 1.19.3. The name may be a legacy one (not verified) | verified, 1.19.3 only | Generated routing goes to `config.json`. The resolved-model check detects a version that stops reading it. Runtime use of `config.json` itself was verified in experiment E5 (step 1b.5): a routed subagent ran on its routed model |
| F37 | An `agent.<name>.mode` entry in a config file is ignored: a subagent stays a subagent, and `run --agent` on it still falls back (stderr warning, exit 0) | verified, 1.19.3 only | Evidence E6. A primary-mode copy of the agent file is needed (F6, F39) |
| F38 | A fallback also loses the routing: the fallback agent `build` ran on `gpt-6-astra`, not on the model routed to the requested agent | verified, 1.19.3 only | Evidence E6. The adapter treats the fallback warning, an agent mismatch and a model mismatch as failures |
| F39 | `OPENCODE_CONFIG_DIR` is read: an `agents/<name>.md` there beats the global agent of the same name, and the model still comes from `OPENCODE_CONFIG`. A real run on it had no fallback and used the routed model | verified, 1.19.3 only | The runner never writes into the target repo: it creates a temporary config folder per run (step 2.1) |
| F40 | A project `.opencode/agents/<name>.md` with a `model:` line beats the routing, also when the config-dir copy exists; the other fields appear to merge between the two files | verified for the model, merge not tested per field | The preflight fails on any `.opencode/agents/<role>.md` in a target project (step 2.2) |
| F41 | A project `.opencode/opencode.json` is read like a project `opencode.json`: an agent model set there resolves | verified, 1.19.3 only | The preflight flags `agent.*.model` in it (step 2.2) |
| F42 | A model id that does not exist: exit 1 in about 10 s, empty stderr, three `error` events (the same message twice, then a generic one with a `ref`), the text in `error.data.message`, no model call | verified, 1.19.3 only | The adapter lists each distinct message once; sample in `tests/fixtures/opencode-run/bad-model.jsonl` |
| F43 | The run events are `step_start`, `text` and `step_finish` (`reason`, `tokens`, `cost`); no event names the model. The assistant message of `opencode export` (`messages[1].info`) holds `agent`, `mode`, `modelID`, `providerID` and `finish`; the session `info.model` and the user message hold the requested model | verified, 1.19.3 only | The model that ran is read from the export; the fallback shows as agent `build` |
| F44 | `opencode export` takes about 4.3 to 5.6 s (7.7 s once, cold); `--pure` is not faster | verified, 1.19.3 only | The runner exports once per run and only when the events look clean |
| F45 | The real `code-reviewer` writes an analysis section before its JSON (a reply that starts with a heading and ends with one fenced block) when only the attached task file asks for JSON. When the task file and the task message both say that the whole reply is the JSON and that this overrides the output format in the agent's instructions, it replied with a bare JSON object | verified on haiku only, one run each | `parse_report` stays strict. Check GPT and Gemini in step 2.5; if prose comes back, decide whether the last fenced block may count (a design decision). Evidence E7 |
| F46 | A real review of a tiny diff by the real `code-reviewer` on haiku took 52 to 101 s and cost $0.02 to $0.04 (the longer run used 44k tokens and loaded skills through tool calls, F11); no run folder was left in the temp folder and the target repo stayed clean | verified, 1.19.3 only | Part of per-run cost in the benchmark. Evidence E7 |
| F47 | The real `code-reviewer` on its production model (`gpt-5.6-terra`), started through the command line entry on a ready target, replied with a bare JSON object: execution and artifact success, 110 s, $0.089, requested and resolved model equal. The GPT family obeys the JSON-only wording like haiku did (F45); Gemini is untested | verified, one run, 1.19.3 only | The benchmark repeats this per family (step 2.5). Evidence E8 |
| F48 | Three runs on two models (haiku twice, gpt-5.6-terra once) cited line 8 for a bug on line 3 of the file; line 8 is the added line in the sample patch file, so the line a finding cites may count lines of the patch, not of the file | observed on one diff, three runs | The benchmark scores both readings (`line_basis`), and the task message may have to say which line is meant. Evidence E8 |
| F49 | In the 63 run benchmark (E9), 37 of the 43 runs that found the bug cited the line of the patch file and none cited the line of the changed file; the other 6 cited neither (not examined) | verified, one benchmark, 1.19.3 only | The task message now says which line to cite; a rerun shows whether the models follow it. Evidence E9 |
| F50 | claude-sonnet-5 refused the JSON-only instruction in 2 of 21 runs, both on `retry-swallows-error`: it called the task file an injected instruction and replied in prose. GPT and haiku followed the same wording in every run | verified, 2 runs on one case | The wording no longer says that it overrides the agent's instructions and says why the format is needed. If sonnet still refuses, add a JSON mode section to `agents/code-reviewer.md` (a live change, decision needed). Evidence E9 |
| F51 | One haiku run (`clean-guard-with-test` #3) stopped with stop reason tool-calls: the agent tried to read a path in the temp folder, outside the target project, and the headless run rejected the permission request (`external_directory`, F13). It was recorded as an execution failure | verified, 1 of 63 runs | The task message now says that the attached files are included in the message. Evidence E9 |
| F52 | An agent-level `variant` in the config reaches the request: with `high`, the session export records `variant: high` on the assistant message and the reasoning tokens went from 0 to 47. A level the model does not offer (`xhigh` on claude-haiku-4.5, which offers `high` and `max`) is ignored silently: exit 0, empty stderr, the variant stays `default` | verified on one model, 1.19.3 only | The profile gets an optional `effort`, rendered as `variant`. A run compares the export with the requested effort and fails when they differ, like the model check (F34). The level `none` is untested. Evidence E10 |
| F53 | `opencode models github-copilot --verbose` lists `variants` for every model. Most offer low, medium, high, xhigh and max; claude-haiku-4.5 offers only high and max; gpt-5.3-codex has no max; gpt-5.6-luna, gpt-5.6-sol, gpt-5.6-terra, gpt-6-luna and gpt-6-sol also offer none | verified, 1.19.3, 2026-10-25 | The policy keeps no per-model effort list: OpenCode is the source and a copy would go stale. Evidence E10 |
| F54 | OpenCode checks each part of a chained bash command against the rules separately. With the fallback `deny` and the one allow `echo ok *`, `echo ok one` ran, while `echo ok two; ...`, `echo ok three && ...` and `echo ok four | tee ...` were denied by the rule and wrote no marker file | verified, one model, one run, 1.19.3 only | Resolves F31 for trailing wildcards: an allow such as `python -m unittest *` does not let a chained command through. Patterns with a `*` in the middle were not tested. A `cd <path> && command` asks for its `cd` part, so the task prompt says not to cd. Evidence E11 |
| F55 | A machine sleep during a benchmark run makes the run look hung: 4 of 105 runs were recorded as 'did not finish within 600 s' with durations of 1,114 to 16,288 s, and a fifth finished normally but took over 700 s. In the two I inspected, the reply and the stop event had arrived within seconds of the start. The person running it reported that the computer went to sleep; the system log was not read | user-reported, 1.19.3, Windows | The runner marks a run whose wall time is far over the timeout (`Outcome.slept`); the benchmark leaves such rows and timeouts out of the numbers and `--resume` repeats them. The timings of the candidate benchmark are not usable. Evidence E12 |
| F56 | Started with `nohup ... &` and no stdin redirect, every OpenCode run failed with `EBADF: bad file descriptor, read` and exit code 1, without a model call (105 of 105 runs, in a few minutes). With `< /dev/null` a 2 run smoke test and the full benchmark worked | verified, 1.19.3, Windows | The runner passes `stdin=subprocess.DEVNULL` itself, so it no longer depends on how it was launched. The benchmark stops after 5 runs that all failed before any model answered. Evidence E12 |
| F57 | gpt-6-luna on the real `code-reviewer`: 7 bugs found in 15 runs (5 of the 12 valid bug runs missed) and 5 of 6 clean diffs blocked, where the other four models found every bug they produced a report for and blocked no clean diff. In one reproduction on a clean diff it stopped at the static-analysis precheck ('the changed files were not found in the workspace') and returned REQUEST CHANGES with a BLOCKING finding before reviewing any code; a second reproduction ended with stop reason tool-calls and no reply | verified in the benchmark; the cause rests on two reproduction runs | gpt-6-luna stays experimental. Whether the precheck fails on the benchmark targets for every model is not investigated. Evidence E12 |
| F58 | One of the two undiagnosed failures of the 2026-10-25 retest: claude-sonnet-5 on `off-by-one-loop` #2 stopped with stop reason tool-calls and no reply; stderr: `permission requested: bash (echo done); auto-rejecting`. The reviewer asked to run a bash command outside its allow list, the headless run rejected it (F13) and the run ended | verified, 1 run | Same stop reason as the haiku run of F51 and two luna runs of F57 (their stderr was not seen). A reviewer that tries an unlisted command can end a headless run without a reply. It counts as an execution failure; a task message that forbids other commands is untested. Evidence E13 |
| F59 | The other failure: claude-haiku-4.5 on `clean-guard-with-test` #3 started its reply with prose ('Perfect. Static analysis passed. Now let me review...') and a fenced JSON block followed (the end of the reply was not seen). `parse_report` accepts only a reply that is the JSON, so it was an artifact failure | verified, 1 of 9 haiku-4.5 runs in the retest | The F45 shape again after the wording change of F49 to F51. `parse_report` stays strict; whether the last fenced block may count is an open design decision (the cost is a looser contract). Evidence E13 |
| F60 | The unit test suite takes 60 to 120 s (82 s in a measured run of 501 tests); the validator takes 6 s. The slowest test takes 2.9 s and the 12 slowest modules account for 73 s. Their tests start git and python processes (seen in the setup code of quick_lane_check, git_context and entry_points) | measured, Windows | No hot spot, so it was not optimised: copying a template repository would remove only the setup git calls (an estimate: about 3 of 10 process starts per test). Agents run the one relevant test module and the full suite once before the commit. Evidence E13 |
| U1 | `--session` can be used for retry | unverified | Do not rely on it in `report.py` |
| U2 | `bash: "*": deny` in a derived agent is parsed exactly as assumed | verified | Step 0.5 evidence |
| U3 | Cause of one failed GPT benchmark run | not reproducible | The spike code and its output are not in the repository (F12), so the cause cannot be found. The real `code-reviewer` on gpt-5.6-terra passed the execution and artifact levels (F47); the benchmark records every failure with the error text, the stderr tail, the event tail and the reply head, so a repeat can be diagnosed (step 2.4) |
| U4 | The global `opencode.json` permissions still apply when `OPENCODE_CONFIG_DIR` is set | verified, 1.19.3 only | `debug agent code-reviewer` gives the same 140 permission rules with and without the per-run config folder, the same order outside the skill folders, and `edit`, `write` and `task` end in deny. No extra permission step is needed in the runner. Evidence E7 |

## 3. Target folder structure

```text
ai-framework/
├── agents/                       # role + prompt + permissions per agent; no `model:` line (validator-enforced)
├── execution/                    # NEW: everything about running and verifying
│   ├── policy.json               # { "models": {...}, "constraints": { "independence": [...], "protected_paths": [...] } }
│   ├── profiles/
│   │   ├── default.json          # agent -> model, the only place; optional `capability` note per agent (documentation only)
│   │   └── bench-*.json          # benchmark profiles
│   ├── routing.json              # GENERATED from the default profile; linked as ~/.config/opencode/config.json
│   ├── schemas/                  # contracts between stages (policy, review-report, qa-report, run-record; the profile and routing have none, see step 1b.2)
│   ├── runner/                   # thin runner, OpenCode only (replaces the unclear name adws)
│   │   ├── runner.py             # orchestrates one run
│   │   ├── resolve.py            # policy filter, constraints, resolved-model check, fallback
│   │   ├── opencode_adapter.py   # derive primary-mode agent copy, benchmark routing via OPENCODE_CONFIG, run headless, parse events
│   │   ├── report.py             # envelope parse/validate, retry, success levels
│   │   ├── record.py             # RunRecord (JSONL)
│   │   └── pipeline_review_qa.py # Phase 3C: throwaway experiment (MAX_FIX_LOOPS=3)
│   └── execution/verification/             # deterministic facts
│       ├── checks/               # branch_protection, dependency_change, protected_paths, diff_size, build, tests, format, ...
│       ├── gates/                # compose checks: pre_push, post_review
│       └── run.py
├── hooks/                        # existing; become thin entrypoints calling execution/verification/
├── tools/
│   ├── validate_framework.py     # renamed from validate_agents.py (wrapper kept for transition)
│   ├── generate_routing.py       # NEW (step 1b.2): profile -> execution/routing.json
│   └── lib/
│       ├── frontmatter.py        # strict parse
│       └── opencode_models.py    # provider-specific discovery (isolated here)
├── tests/
│   ├── fixtures/                 # valid + intentionally invalid
│   ├── test_*.py                 # unittest
│   └── bench/                    # permissions-evidence.md, git-permissions-evidence.md, model-routing-evidence.md, bench.py, bench_cases.py, baseline profile
├── docs/
│   ├── transition-plan.md        # this file
│   └── decisions/
│       ├── DEC-011-...md         # Status: Superseded by DEC-016
│       ├── DEC-013, DEC-014      # unchanged
│       ├── DEC-015-deterministic-verification.md
│       ├── DEC-016-role-profile-policy.md
│       ├── DEC-019-...md         # model routing (decisions #4 and #8); supersedes the roles/ and access-translation parts of DEC-016
│       ├── MODEL-ASSIGNMENT-MATRIX.md  # step 4.3: generated from policy + profile, or replaced by a printed view
│       └── evaluations/          # one file per experimental model that gets promoted
├── skills/ commands/ instructions/ scripts/   # unchanged; skills stay runtime-agnostic
├── git-template/                 # generated by setup.py (unchanged mechanism)
└── setup.py                      # small additions only until Phase 5 (link routing.json as config.json, step 1b.6); simplified in Phase 5
```

Source of truth:

| Information | Source of truth |
|---|---|
| Role responsibility, prompt, permissions | `agents/*.md` (no model) |
| Which model runs an agent | `execution/profiles/default.json` |
| Routing as OpenCode reads it (derived) | `execution/routing.json`, generated by `tools/generate_routing.py`, linked as `config.json`; the validator fails on drift |
| Which models are legal, families, experimental status | `execution/policy.json` (`models`) |
| Independence rules, protected paths | `execution/policy.json` (`constraints`) |
| Contracts between stages | `execution/schemas/` |
| Workflow definition | The Phase 3C hardcoded pipeline (experiment only) |
| Deterministic rules and gates | `execution/verification/` |
| Runtime invocation | `execution/runner/opencode_adapter.py` |
| Evidence of what ran | `execution/runner/runs/*.jsonl` |
| Why decisions were made | `docs/decisions/` |
| Human-readable model matrix | Generated from policy + profile, or a printed view (step 4.3) |

## 4. Phases

Rules for every phase:
- Each commit is atomic and independently verifiable.
- Do not start a step before the previous step's test passes. If a test fails, fix or revert, never stack.
- No step deletes anything until Phase 4, with one exception: Phase 1b moves the `model:` lines out of the agent files into the profile. The profile is seeded from those lines first (step 1b.2), and the resolved models are compared before and after (step 1b.5).
- Check the commit-msg hook format before the first commit of a phase.
- Merge at phase exit through a pull request (see "Working method").

### Phase 0: baseline, inventory and permission evidence (1-2 days)

Do 0.5 and 0.6 first. They test the two assumptions the architecture rests on. If either fails, stop and rethink Phase 2 before writing any code.

| Step | Do | Test |
|---|---|---|
| 0.1 | Create the Phase 0 branch and worktree | branch exists, `git worktree list` shows two folders (done) |
| 0.5 | Negative permission test. In a throwaway repo, run a derived read-only reviewer and ask it to: edit a file, write a new file, delegate through `task`, and run a shell command that writes. Record results in `tests/bench/permissions-evidence.md`; update the F4, F5 and U2 statuses | `git status --porcelain` is empty afterwards (`git diff --exit-code` alone misses new untracked files) |
| 0.6 | Git permission tests in a throwaway repo with a local bare remote (`git init --bare remote.git`), using the rule block from section 6 with the catch-all first: (1) branch and commit with no prompt, (2) push a feature branch with no prompt, (3) `git push origin main` is denied, and `git push origin HEAD:main` is stopped by the hook or noted as a gap, (4) `npm install lodash` prompts | all four behave as expected; settles decision #3 and the F9 status |
| 0.2 | Record 3-5 real past tasks on the current flow: outcome, review iterations (and cause: implementation / review / verification / environment / unclear requirement), time, tokens, what gatekeeper caught or missed. Project data stays out of this repo, so keep the file outside it (for example `/d/ai-framework-private/baseline.md`) | the private file exists with 3-5 tasks and no empty fields ("unknown" allowed); `git grep` finds no project names in this repo |
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
| 1.5 | Read-only rule: any agent with `edit: deny` must also deny `write` and `task`. Fix the real agents. Exemptions are recorded in `READ_ONLY_EXEMPTIONS` (qa: write, orchestrator: task) | fixture fails; real agents pass after fix; a throwaway project shows `task` denied for the edited agents (F17) |
| 1.6 | `execution/policy.json` as data, grouped into `models` and `constraints`. Per model: `family` (`claude`, `gpt`, `gemini`; independent of provider, so `github-copilot/claude-sonnet-5` and `anthropic/claude-sonnet-5` are both `claude`), `status` (approved / experimental), `evaluation` path for promoted ones. Independence edges move from code into `constraints` | validator reads policy; DEC-014 fixtures (same model for planner and reviewer, experimental without evaluation) both fail |
| 1.7 | Rename to `validate_framework.py`, keep `validate_agents.py` as a wrapper | both entry points pass |
| 1.8 | Lint: framework-owned verification and schema files (`execution/verification/`, `execution/schemas/`) must not contain concrete model ids or provider names. Match ids (`claude-`, `gpt-`, `codex`, `o1`/`o3`-style, `gemini-`, and provider prefixes such as `anthropic/`, `github-copilot/`), not prose mentions such as "GPT models may..." | fixture with a model id fails; fixture with a prose mention passes |
| 1.9 | Apply the git and dependency permission rules from section 6 to the global `opencode.json` (catch-all first) and add the human-in-the-loop rules to `AGENTS.md`. The global `opencode.json` and `AGENTS.md` are links into this repo (F16), so edit the repo copies and test them in a throwaway setup before merging. Move the catch-all first and tighten patterns such as `git push*main*` | rerun the 0.6 tests against an isolated copy of the config (`XDG_CONFIG_HOME`, F19); plus: on a `feat/x` branch, an unrelated request makes the agent ask "same branch or new one?" |

Exit criterion: the validator rejects the first two DEC-014 incident types (the same model for planner and plan-reviewer, and an experimental model without an evaluation). The third (a gatekeeper tier decided by hand) is addressed in step 3A.4. This phase is valuable even if everything after it is abandoned. Merge to `main` at exit.

### Phase 1b: model routing (2-3 days, changes live behavior)

Added 2026-10-18 after experiments E1 to E4 (E1 missing model, E2 frontmatter against config, E3 extra config files, E4 precedence; F32 to F36) and decisions #4 and #8. Branch: `feat/phase-1b-model-routing`. This phase removes the model from the agent files. That is the one step that can silently put an agent on its caller's model (F34), so do the steps in order and test in a fake home (F19) before merging. It comes before Phase 2 because the Phase 2 benchmark swaps models through a generated routing file.

| Step | Do | Test |
|---|---|---|
| 1b.1 | Record E1 to E4 in `tests/bench/model-routing-evidence.md` (setup, commands, results behind F32 to F36). Write DEC-019 (next free number): model routing through a generated `config.json`; supersedes the `roles/` and access-translation parts of DEC-016; records decisions #4 and #8 | each of F32 to F36 points to the evidence file; `grep -rn "DEC-019" .` resolves |
| 1b.2 | `execution/profiles/default.json`, seeded from the current `model:` lines of all agents. An optional `capability` note per entry (for example `high_reasoning`, `coding`) is documentation only: nothing reads it. `tools/generate_routing.py` renders the profile into `execution/routing.json` (`{"agent": {"<name>": {"model": "<id>"}}}`). No schema files for the profile and routing (decided 2026-10-21): `load_profile` in `tools/lib/routing.py` is the validation, and a schema file would be a second copy that can drift. Add them only if an editor or another tool needs to consume one | generator output equals a fixture; a second run changes nothing. Done. The generator writes a first `"$schema": "https://opencode.ai/config.json"` line, because OpenCode adds it to a global `config.json` that lacks it and, through the link, would rewrite the repo file |
| 1b.3 | The independence and experimental-model checks (steps 1.4 and 1.6) read the profile instead of the frontmatter | the DEC-014 fixtures still fail; the real profile passes |
| 1b.4 | New validator checks: (a) no `model:` line in `agents/*.md`; (b) no `agent.*.model` entry in the repo's `opencode.json`; (c) every agent has a profile entry and every entry has an agent; (d) `execution/routing.json` equals the generated output; (e) resolved check: `opencode debug agent <name>` prints the profile's model for every agent (no model call; skipped with a clear message when `opencode` is not installed) | one failing fixture per check; the real repo passes after 1b.5. Done: (a) is enforced by `check_model_lines` since the `model:` lines were removed (PR #55); the temporary checks `check_frontmatter_conflicts` and `check_profile_matches_agents` and their tests are gone |
| 1b.5 | In a fake home (F19, copy of the files): link `routing.json` as `config.json` and remove the `model:` lines. Compare `opencode debug agent` before and after for all 15 agents. Then one cheap headless delegation (a primary agent calling a subagent, as in E1) and read the model the child session recorded | resolved models are identical before and after; the child ran on its routed model, not its caller's. This is the runtime test of `config.json` itself, which E1 to E4 did not run. Done as experiment E5 (recorded in the evidence file, F34 and F36): with the 15 `model:` lines deleted and only `config.json` present, OpenCode resolved the profile model for all 15; a control without `config.json` gave 15 times no model resolved; a routed subagent child session recorded its routed model |
| 1b.6 | `setup.py` links `execution/routing.json` as `~/.config/opencode/config.json`, the same way as `opencode.json`; `--verify` runs check (e). One characterization test for this link only | fresh clone: `git pull` plus `python setup.py` gives a green validator; with the link removed, `--verify` fails and names the routing file. Done |
| 1b.7 | No per-project model overrides (decision #4): the validator, and from Phase 2 the runner preflight, flag `agent.*.model` in a project's `opencode.json` and in a file named by `OPENCODE_CONFIG`. The runner's own benchmark routing (Phase 2) is the only allowed use of `OPENCODE_CONFIG`. Split 2026-10-21: the repo level is done (check (b), `agent_model_problems`); the project level is part of the runner preflight in step 2.2, because the validator cannot see other projects | fixture: a project `opencode.json` that sets an agent model is flagged. Repo level done; project level is tested with step 2.2 |

Exit criterion: all 15 agents resolve to the same models as before, no agent can start without a profile entry, and the install bar from section 7 holds. Live-merge hazard: after `git pull` of this phase the agent files have no model, so every agent inherits its caller's model until `python setup.py` has linked `config.json`. Run `python setup.py` right after the pull; `--verify` fails loudly if the link is missing.

Status 2026-10-21: Phase 1b is complete in code and merged. The agent files have no `model:` line (enforced), the profile is the only routing, `config.json` is linked and `--verify` reports `Model routing: OK`. The one part left is the project-level half of 1b.7, which moved to step 2.2. No schema files were written for the profile and routing (step 1b.2).

### Phase 2: reviewer runner inside the repo (3-4 days), decision gate

Status 2026-10-22: merged so far: the contracts (`contract.py` and the two schemas), `resolve.py`, `report.py` and `record.py`, and `opencode_adapter.py` (event parser, export reader, fallback and wrong-model checks, `derive_agent` and the per-run setup helpers), all tested against real samples in `tests/fixtures/opencode-run/`. Merged since: `run.py` (the runner: per-run config folder, OpenCode, export, report check and `RunRecord`) with a task message that demands a JSON-only reply (F45). A live run of the real `code-reviewer` on haiku passed the execution and artifact levels (E7). Merged since: the preflight (`preflight.py`, called by `run_review`: project agent models, a project agent file for the role, and the first-run files) and a command line entry (`python -m execution.runner.cli`). Merged since: the benchmark (`bench_cases.py`: 7 cases, 5 with a planted bug and 2 clean; `benchmark.py`: runs every model through the same runner, scores the replies in code and prints review flags). Benchmark of 2026-10-24 (E9): 63 runs with gpt-5.6-terra (baseline), claude-haiku-4.5 and claude-sonnet-5 on 7 cases, 3 repeats each. Valid reports 21, 20 and 19 of 21; bugs found 15, 15 and 13 of 15 (both misses are runs without a valid report); false positives 0 of 6 for each model; no violations and no fallbacks. Gate status: provisional. The hard requirements hold for two families (Claude and GPT) except schema validity, which is 100%, 95% and 90% by model (F50, F51). Gemini is not offered by the configured providers and is added later. Retest of 2026-10-25 (27 runs on the failing cases and the line case, after the wording change of F49 to F51): valid reports 9, 8 and 8 of 9 for gpt-5.6-terra, claude-haiku-4.5 and claude-sonnet-5; bugs found 6, 6 and 5 of 6; no false positives and no violations. Sonnet's earlier refusal did not come back (3 of 3 valid on `retry-swallows-error`). Two other runs failed (an execution failure on sonnet and an artifact failure on haiku) and have not been diagnosed. The file line was cited in 3 of the 17 runs that found the bug, so the line wording helps only a little. The gate stays provisional. Phase 3A has started as a pilot of the framework itself: its own orchestrator flow implemented the `protected_paths` check in a worktree (35 orchestrator messages; 6 bash commands were refused by the deny-by-default rule and retried with allowed ones). It was reviewed here, and one fail-open case (a protected path of `.` or an empty string) was fixed in a second step. Model list and reasoning effort were updated on 2026-10-25 (F52, F53, E10). Candidate benchmark of 2026-10-26 (E12, 105 runs: the baseline gpt-5.6-terra and the trial models claude-haiku-5.5, claude-sonnet-5.5, gpt-6-luna and gpt-6.1-sol): the baseline, haiku-5.5, sonnet-5.5 and gpt-6.1-sol found every bug they produced a report for and blocked no clean diff; gpt-6-luna found 7 of 15 and blocked 5 of 6 clean diffs (F57). Five runs were invalid: four across a machine sleep (F55) and one that stopped on a tool call. The timing columns are not usable. The reviewer must stay in a different family from the Claude producers, so only the GPT candidates are relevant for that role. The runner now passes an empty stdin (F56), marks runs that slept, and the benchmark has `--resume` and stops early when the setup is broken. Evaluation records were added on 2026-10-26 for claude-haiku-5.5, claude-sonnet-5.5 and gpt-6.1-sol (they stay experimental, so a profile may use them but they are not approved; gpt-6-luna has none). Findings of 2026-10-28: the two undiagnosed failures of the 2026-10-25 retest are explained (F58, F59) and the slow test suite is not worth optimising (F60). Phase 3A pilots: the framework's own orchestrator flow implemented the `protected_paths` check, a fix for empty and dot paths followed, and a second pilot step rejected leading-slash paths on Windows (all merged); the method, the prompt rules and the checks are in `docs/pilot-runbook.md` and the numbers in E13. Still to do: the remaining 3A steps (`branch_protection` and `dependency_change` as the next pilot, then the gates, the hook split and the gatekeeper trim) and Gemini (not offered by the configured providers).

| Step | Do | Test |
|---|---|---|
| 2.1 | Write the runner in `execution/runner/` (the earlier spike code is not in the repository, F12), split into `resolve.py`, `opencode_adapter.py`, `report.py` and `record.py` (plus `contract.py`, the schema checker, `run.py`, which joins them, `preflight.py`, `cli.py`, `bench_cases.py` and `benchmark.py`). The adapter runs the real agent as a primary agent without writing into the target repo: per run it writes a temporary config folder with a derived copy of `agents/<name>.md` (only the `mode:` line becomes `primary`, no `model:` line; F6, F37) and a run config with the model, and starts OpenCode with `OPENCODE_CONFIG_DIR` and `OPENCODE_CONFIG` pointing at them (F35, F39). The model that ran is read from the assistant message of `opencode export` (F43). It checks the model that actually ran against the profile (F34); for delegations the task result carries `metadata.model`. Before writing the event parser, capture a real JSON sample from `opencode run --format json` in a throwaway project: the parser is not written from memory. The reviewer report is a schema in `execution/schemas/` and the task message states it | offline unit tests: resolve rejections, event parsing from the captured sample, report validation, fallback warning caught, model mismatch caught; derived agents checked with `opencode agent list` in a throwaway project (F17) |
| 2.2 | Implement the three success levels (section 5.3) and the minimum `RunRecord` fields (section 5.4). On failure, records include the stderr tail and event tail, and the start of the reply when the report check failed (`error.reply_head`). Add a runner preflight in code that requires `docs/project-overview/stack.md` with content and `.ai-framework.json` in the target repo, and fails with a readable message instead of skipping (see `docs/inventory.md`, section 4). The preflight also applies decision #4: it fails when a project `opencode.json` or a file named by `OPENCODE_CONFIG` sets `agent.*.model` (the runner's own benchmark routing is the only exception), when a project `.opencode/opencode.json` does (verified: OpenCode reads it, F41), and when the target project has any `.opencode/agents/<role>.md` (its `model:` line beats the routing and its other fields merge into the agent, F40) | a forced failure produces a readable error; a repo without `.ai-framework.json` fails preflight with a readable message; a project `opencode.json` that sets an agent model fails preflight; a project `.opencode/agents/<role>.md` fails preflight; a run with "I couldn't complete the review" is execution success but not artifact success |
| 2.3 | Benchmark rework: replace the debatable `zero-division` fixture, add 4-6 harder cases (subtle logic error, bug hidden behind a passing test, cross-file context), tighten detection regexes, add a `baseline` profile that runs the real `code-reviewer` prompt in primary mode | fixtures build; offline summary works. Done: 7 cases in `execution/runner/bench_cases.py` (a plain control, a subtle rule change, a bug behind a passing test, a cross-file bug, a security bug, and 2 clean diffs); the baseline is the production model of `code-reviewer` run with the real prompt through the same runner, and every other model differs only in the profile (`benchmark.py`) |
| 2.4 | Investigate the failed GPT benchmark run (error not yet seen) | cause identified, handled or documented; U3 resolved. Documented: the failed run cannot be reproduced (see U3) |
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
| 3A.2 | `execution/verification/checks/*` (one file per fact) and `execution/verification/gates/*` (compose checks). Includes `branch_protection` (explicit protected-branch list, fails closed when it cannot decide), `dependency_change` (flags diffs to `package.json`, `package-lock.json`, `yarn.lock`, `pnpm-lock.yaml`, `pom.xml`, `build.gradle*`, `requirements.txt`, `pyproject.toml`; blocks the push unless the commit carries a `Dependency-Approved:` trailer) and `protected_paths` (before/after tree diff against `constraints.protected_paths`). `hooks/` become thin entrypoints calling `execution/verification/run.py`; keep the hard-link mechanism in `add_git_template` and add the new files to its tuple | per check: one passing and one failing fixture; a manifest change without the trailer is blocked at push; a commit with the `Lane: quick` trailer over the limits is blocked at push (DEC-018); fresh clone blocks a bad push on Windows |
| 3A.3 | Hook interpreter risk: hooks written in Python need `python3`/`python` resolvable from Git Bash. `setup.py` adds an "action required" entry if not | tested on this machine |
| 3A.4 | Trim `gatekeeper` to judgment-only items; replay the baseline tasks | no more misses than baseline; then decide whether the tier can drop |

**Gate 3A.** Fresh-clone test in a throwaway clone passes, and gatekeeper replay shows no regression. Otherwise stop here: 3A is valuable without 3B and 3C.

### Phase 3B: additional roles (3-5 days)

| Step | Do | Test |
|---|---|---|
| 3B.1 | `qa` agent through the same runner (QAReport schema in `execution/schemas/`, profile entry, no `model:` line) | passes the model-swap test across families |
| 3B.2 | `plan-reviewer` role | passes the model-swap test across families |

**Gate 3B.** Proceed to 3C only if both roles pass the swap test and the Phase 2 results still hold.

### Phase 3C: pipeline experiment (3-5 days, throwaway)

This is an experiment to learn whether multi-role execution is worth building. It is not a workflow engine. Keep the pipeline hardcoded and local, with no configuration-driven stages.

| Step | Do | Test |
|---|---|---|
| 3C.1 | Permissions for implementation roles in the runner: write-allowed gate using `constraints.protected_paths` (decision #1) | only allowed paths change; protected paths (`hooks/`, `agents/`, `.ai-framework.json`, `execution/policy.json`, `execution/profiles/`, `execution/routing.json`, `setup.py`) never change |
| 3C.2 | `pipeline_review_qa.py`: reviewer -> qa -> quality commands (argv lists from `.ai-framework.json`, exit code, last 50 lines) -> gates; `MAX_FIX_LOOPS = 3`; stop reason is readable and no LLM decides to stop | happy path accepted; injected failing test loops then stops at 3 |

**Outcome (recorded in DEC-015):** keep as is, replace with a declarative definition, or remove, based on evidence.

### Phase 4: soak and cleanup (2-3 days)

| Step | Do | Test |
|---|---|---|
| 4.1 | Moved to Phase 1b (steps 1b.2 to 1b.4). With no `roles/` layer, the generator renders only the routing file | covered by 1b.4 and 1b.5 |
| 4.2 | Moved to step 1b.6 (`setup.py` links `routing.json` as `config.json`) | covered by 1b.6 |
| 4.3 | `MODEL-ASSIGNMENT-MATRIX.md` becomes a view generated from policy and profile, or is removed if a printed view is enough (decide here); DEC-011 marked Superseded by DEC-016 | matrix equals generated output; the temporary matrix and policy sync tests (`RealPolicy` in `tests/test_policy.py`) are removed |
| 4.4 | Done in step 1b.5 (resolved models before and after) | covered by 1b.5 |
| 4.5 | Soak: 5 real PRs on the new path; compare with baseline (escapes, retries, time, tokens) using the parity classes from 0.4 | verdict recorded in DEC-015: keep, extend, or revert; section 7 criteria re-checked |
| 4.6 | Bump `FRAMEWORK_VERSION`, `CHANGELOG.md`, update `docs/session-summary.md` | version consistent |
| 4.7 | Instruction entry points for each tool: check how Copilot, Codex and Gemini CLI load `AGENTS.md`; add thin pointer files where a tool uses its own filename (for example `GEMINI.md`) | each tool picks up the same instructions |
| 4.8 | Optional: `new-role <name>` scaffold command that creates `agents/<name>.md` from a template and a profile entry | a scaffolded agent passes the validator |

Nothing is deleted before 4.5 passes. After it: remove the obsolete matrix text and the temporary matrix and policy sync tests.

### Phase 5: documentation and setup cleanup (3-5 days, after the Phase 4 soak)

Added 2026-10-17. These three jobs wait for Phase 4 because each one describes or edits something that Phases 3A and 4 still change: the README documents the final structure and the procedure for changing a model (Phase 1b changes it), and `setup.py` gets additions in steps 1b.6 and 3A.3. Rules: nothing is deleted without a recorded reason, `docs/decisions/` is never touched, and the install bar from section 7 stays (`git pull` plus `python setup.py` reaches a green validator).

| Step | Do | Test |
|---|---|---|
| 5.1 | Evidence inventory (read-only, may run earlier). Extend `docs/inventory.md` with every README section; every `setup.py` function (what it does, and whether a test or the fresh-clone run exercises it); and every file in `docs/` outside `docs/decisions/`, with its `git grep` reference count and a verdict of keep, merge or delete. Also record what produces a per-agent usage table (model and consumption) today (decision #6) | you review the inventory; no other file changes |
| 5.2 | Docs cleanup: apply the 5.1 verdicts. Always kept: all of `docs/decisions/`, `docs/transition-plan.md`, `docs/session-summary.md`, and any file the validator or a test reads | validator and `python -m unittest` green; `git grep` for each removed file name finds no live reference |
| 5.2b | Folder and file merges, from the 5.1 inventory, one commit each with the evidence in the message. Candidates (`git grep` evidence of 2026-10-18): `monitoring/` holds one file (`monitoring/README.md`, 47 lines), referenced by the ccusage installer in `setup.py` and mentioned in `docs/session-summary.md`; decide together with decision #6 whether it moves into `docs/` or stays. Root `workflow-guide.md` (194 lines) is listed in the README structure and in `docs/session-summary.md`, and `skills/first-run-analysis/SKILL.md` mentions appending to a `workflow-guide.md`: check which file that skill means before moving anything. `scripts/` against `tools/` is probably a README clarification (scripts are linked into the OpenCode config, tools are framework-only). `instructions/`: together with step 4.7. `agents/code-reviewer.md` hard-codes `D:\ai-framework\skills\linting-tools\references\*` in `external_directory`, a path into one checkout: decide in 5.2b how it should be written (F18 covers the quoting). Anything linked into the OpenCode config (`agents`, `commands`, `hooks`, `scripts`, `skills`) changes only together with `setup.py` and behind the 5.3 tests | validator and `python -m unittest` green; `git grep` for each moved or removed name finds no stale reference; the fresh-clone run is unchanged |
| 5.3 | `setup.py` simplification. First add characterization tests, because `setup.py` has no tests today: a fresh clone in a throwaway folder, links created, hooks hard-linked, `--verify` output. Then decide per function from 5.1: keep, move the optional installers to their own script, or delete. Before simplifying the graphify wiring, test it in a throwaway folder: `.opencode/` in the live repo holds only the graphify plugin registration, and what created it is unknown (guess: `wire_graphify` runs `graphify install` with `cwd=REPO`). The symlink, junction and hard-link logic changes only after the tests pin its behavior | fresh clone: `git pull` plus `python setup.py` gives a green validator and the same link set as before; `python setup.py --verify` passes on Windows |
| 5.4 | README rewrite: the purpose of every top-level folder and the repo structure; install and update; how to change a model (edit the profile, run `tools/generate_routing.py`, then `python setup.py --verify`); how to resolve common problems (permission prompts, headless `ask` auto-reject, Windows links, missing tools), taken from the F-numbers in section 2. Agent, skill, command and script lists are checked by the validator against the files. Graphify: its output is wanted in every repo that uses the framework, and the developer decides whether to commit it for others or to list it in `.gitignore`; the README documents both options, and the framework never edits a project `.gitignore` for graphify | validator check: every folder, agent, skill, command and script path named in the README exists; a fresh-clone walkthrough that follows only the README works |
| 5.5 | Usage view: a per-agent table of the model used and what each agent consumed, with its data source chosen in decision #6 and documented in the README | the table matches a known run |

## 5. Design rules

### 5.1 Role, model and permissions
An agent file holds the role's responsibility, prompt and runtime permissions, and no model. The validator checks the permissions of the real files (read-only rule, commit-agent denies) and rejects a `model:` line. The model comes only from the profile, rendered into the generated routing file (section 3, F32 to F36). There is no separate `roles/` layer and no access-to-deny translation (decision #8): "read-only" is enforced by the validator rules from step 1.5, not by a second source of truth.

An optional `capability` note per profile entry (for example `high_reasoning`, `coding`) is documentation only. No code reads it; capability-based routing stays deferred. An optional `effort` per profile entry (`none`, `low`, `medium`, `high`, `xhigh` or `max`) is rendered into `routing.json` as the agent's `variant` and checked against the session export after a run (F52, F53). The policy keeps no per-model effort list, because OpenCode lists the levels per model and a copy would go stale.

### 5.2 Contracts and artifact ownership
`execution/schemas/` are the contracts between stages. Stages hand off through artifacts that validate against them, never through implicit agent context.

| Artifact | Owner |
|---|---|
| `review.json` | `code-reviewer` |
| `qa.json` | `qa` |
| Verification results | `execution/verification/` |
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
Protected paths are versioned data (`constraints.protected_paths`), enforced by comparing the working tree before and after a run. The check does not rely on what the agent reports. The snapshot check cannot guard `.git/` for a role that commits, because every commit changes it (found in the 3A pilot): `.git/` stays with the git gates (`branch_protection`), and the snapshot check covers it only for roles that do not commit.

### 5.7 Provider boundary
OpenCode-specific knowledge stays in `opencode_adapter.py`, `tools/generate_routing.py` (the `config.json` format), `opencode_models.py` and the resolved-model check. The runner knows "the requested execution mode was not honored"; the adapter knows how OpenCode expresses that (F6). `execution/verification/` contains no provider or runtime names.

### 5.8 Generated files
`execution/routing.json` and `MODEL-ASSIGNMENT-MATRIX.md` are generated and never edited by hand (from steps 1b.2 and 4.3). The validator detects drift. `agents/*.md` stay hand-written.

## 6. Git and dependency permissions

Decided in DEC-017 and implemented in step 1.9.

- **Autonomous:** read and edit files, create branches, `git add` and `git commit` (orchestrator only), and push and open the draft PR/MR through `scripts/open-draft-pr.py` only.
- **The developer keeps:** (1) publishing, meaning draft to ready and merging; (2) third-party changes; (3) a new task on an existing branch (stay, new from current, or new from base).
- **Approval checkpoints:** the confirmed spec (`@product-manager`, `grill-me`) and the HLD with its PR breakdown (`@architect`, checked by `@plan-reviewer`).
- **Permissions:** the global `opencode.json` has the catch-all first. The orchestrator's own block repeats the denies, because its own `"*"` rule overrides the global ones (F20). The validator enforces both (`lint_opencode_config`, `lint_commit_agents`).
- **Fast lane:** `/quick`, declared by the developer only (DEC-018). It skips the spec grill, the HLD, the plan review and the PR breakdown, and keeps every review, test and gate step. `scripts/quick-lane-check.py` measures it: at most 3 files and 60 changed lines, and no manifest, lockfile or `.ai-framework.json`. Over the limit, the orchestrator stops and the developer decides.
- **Backstops still to build (3A):** `branch_protection`, `dependency_change`, and server-side branch protection.

## 7. Acceptance criteria

Checked at the Phase 2 gate and again at 4.5. A phase that breaks one is a reason to stop or simplify, the same way a failed benchmark is.

- **Install and update stay simple.** A fresh clone reaches a green validator with no steps beyond today's (`git pull` + `python setup.py`).
- **A new role is cheap and safe.** It touches 2 files (`agents/x.md` and a profile entry) and is caught by the validator if misconfigured (a missing profile entry or a `model:` line).
- **Health check is one command.** `validate_framework.py` covers schemas, policy, permissions, the lint and generated-file drift; `python -m unittest` is the second.
- **No Claude-only assumption** in framework-owned files, and a reviewer run passes with one model per family (Claude, GPT, Gemini), changing only the profile.

## 8. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Headless agents stop at global `AGENTS.md` gates (F8) | A pre-approval sentence is not enough for the first-run gate. The runner preflight checks the gate's preconditions in code and fails closed; no headless-specific `AGENTS.md` (step 0.3) |
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
| Live install changes by accident while working | Worktree per phase; throwaway-clone test for 1b and 3A |
| An agent without a profile entry silently runs on its caller's model (F34) | The validator requires an entry for every agent and checks the resolved model with `opencode debug agent`; the runner compares the model that ran with the profile |
| Anything above `config.json` overrides the routing (F35): a `model:` line, `OPENCODE_CONFIG`, a project `opencode.json` | The validator rejects `model:` lines and `agent.*.model` in the repo; the runner preflight and `--verify` flag project-level overrides (decision #4) |
| `config.json` may be a legacy file name that a later OpenCode stops reading (F36) | The resolved-model check fails loudly on every `--verify`; revisit the file name when OpenCode is upgraded |
| Pulling the routing change before `setup.py` links `config.json` leaves agents without a model | The PR description says to run `python setup.py`; `--verify` fails and names the missing link |

## 9. Decisions needed from you

1. **Which paths may implementation roles write, and what must always be protected?** The git permission rules are decided (section 6). The path list decides the 3C.1 write-allowed gate. Decided 2026-10-24: a deny list, because projects differ in layout. Protected: `.git/`, `hooks/`, `.ai-framework.json`, `opencode.json`, `AGENTS.md`, `agents/`, `execution/policy.json`, `execution/profiles/` and `.github/`; everything else is writable. Manifests and lockfiles stay with the dependency-change gate (3A.2). The list becomes versioned data (`constraints.protected_paths`, section 5.6) when step 3C.1 needs it.
2. **Hooks in Python.** Port `pre-commit`, `commit-msg`, `pre-push`, `build-verify.sh` to Python, or keep shell and call Python from them? Can wait until 3A.
3. **Global `opencode.json` ordering.** Move `"*": "ask"` to the top of the bash block so your git allows take effect? Settled by step 0.6: yes, move it first (F9 verified).
4. **Profile location.** Decided 2026-10-18: one default profile in the framework, no per-project override. A project `opencode.json` beats the framework routing (F35), so the validator and the runner preflight flag any agent model in a project file or in `OPENCODE_CONFIG`. A per-project override can be added later together with a run-time re-check against `policy.json`. Repo level enforced since step 1b.4 (b); the project and `OPENCODE_CONFIG` checks belong to the Phase 2 preflight (step 2.2).
5. **Parity margin** for the Phase 2 gate (what difference from the baseline reviewer is acceptable on the directional metrics). Decided 2026-10-24: a review flag, not an automatic rejection. A model is flagged when it misses more than one case worth of bug runs (the number of repeats) beyond the baseline reviewer, or has more than one case worth of false positives on clean diffs beyond it. Percentages are not used because three repeats are too few. `benchmark.py` prints the flags (`review_flags`).

6. **Usage table.** What should the per-agent table show (model, tokens, cost) and where does its data come from: OpenCode session data, the RunRecords from Phase 2, or an existing tool such as ccusage? Answer before step 5.5; step 5.1 records what exists today.

7. **Layout.** Decided 2026-10-18: the runner and the verification code live under `execution/` (`execution/runner/`, replacing the unclear name `adws`, and `execution/verification/`), so one folder holds everything about running and verifying.

8. **Where models live.** Decided 2026-10-18 (E1 to E4, F32 to F36): the model lives only in `execution/profiles/default.json`. Agent files carry no `model:` line. `tools/generate_routing.py` renders `execution/routing.json`, which `setup.py` links as `config.json`. `roles/` and the access-to-deny translation are dropped. Recorded in DEC-019 (step 1b.1). Done in Phase 1b: the `model:` lines are removed and a new one is flagged by the validator.

## 10. What is not changing

`skills/`, `commands/`, `instructions/`, `scripts/`, the symlink and junction logic, the git-template hard-link mechanism, the cross-family validation intent, and all historical DECs. Of these, only the symlink, junction and git-template logic may change, and only in Phase 5 behind the tests in step 5.3. Historical DECs are never deleted.
