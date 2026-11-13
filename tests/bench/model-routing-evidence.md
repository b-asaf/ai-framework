# Model routing evidence (E1 to E16)

Date: 2026-10-18. OpenCode 1.19.3, Windows, Git Bash. Findings F32 to F36 in `docs/transition-plan.md` rest on this file.

## Setup

- Throwaway "fake home": `FH=/d/opencode-fake-home-exp`, agents in `$FH/.config/opencode/agents/`, run with `HOME=$FH XDG_CONFIG_HOME=$FH/.config`.
- Only the config directory is isolated. `opencode debug paths` showed the data directory is still the real one, so the provider login and `~/.claude/skills` were shared with the live install (F11).
- Models: A = `github-copilot/claude-haiku-5.5` (Claude family), B = `github-copilot/gpt-5.4-mini` (GPT family).
- Probe agents (all `mode: subagent`, prompt "Reply with the single word probe."):
  - `probe-a`: `model:` A in the frontmatter, no config entry.
  - `probe-b`: `model:` A in the frontmatter and `agent.probe-b.model` = B in `opencode.json`.
  - `probe-none`: no model anywhere.
  - `probe-cfg`: no `model:` line, `agent.probe-cfg.model` = B in `opencode.json`.
  - `probe-gen`: no `model:` line, used for the extra-config-file tests.
  - `boss`: `mode: primary`, `permission: task: allow`, delegates through `task`.
- Static checks use `opencode debug agent <name>`, which prints the resolved agent without a model call. Runtime checks use `opencode run --agent boss --format json` and read `metadata.model` and `sessionId` of each `task` result, plus `opencode export <sessionID>` for the child sessions.

Caveat: the first static run used the unreplaced placeholders `REPLACE/model-a` and `REPLACE/model-b`. `debug agent` does not validate the id, so the result looked plausible. Everything below comes from the rerun with real ids.

## E2: frontmatter against config (static)

| Agent | Frontmatter | `opencode.json` | Resolved model |
|---|---|---|---|
| `probe-a` | A | none | A |
| `probe-b` | A | B | **A** |
| `probe-none` | none | none | no `model` block |
| `probe-cfg` | none | B | **B** |

Result: a `model:` line in the agent file beats the config. A config entry applies when the file has no `model:` line. (F32, F33 static)

## E1: runtime (agent with no model, and config-routed agent)

Run 1: `boss` on A delegates once to `probe-none` and once to `probe-cfg`.
- Both `task` calls happened. The `task` results carry `metadata.parentSessionId`, `metadata.sessionId` and `metadata.model`.
- The `probe-cfg` child session recorded `gpt-5.4-mini` (B). Its title was "Probe cfg". This confirms F33 at run time.
- The other child recorded `claude-haiku-5.5`, but its title was cut off in the grep window, so the mapping to `probe-none` was inferred from the stream order. Haiku was also the model of `boss`, so run 1 alone could not tell inheritance from a global default.

Run 2: `boss` on B delegates once to `probe-none`.
- The only child recorded `gpt-5.4-mini`. With one delegation there is nothing to infer.

Result: an agent with no model anywhere runs on its caller's model (haiku under haiku, gpt-5.4-mini under gpt-5.4-mini). It is not a global default. (F34)

## E3: extra config files (static, `probe-gen`)

| Setup | Resolved model |
|---|---|
| no extra config (control) | none |
| `OPENCODE_CONFIG=D:/e1-extra.json` (B) | B |
| project-level `opencode.json` (B) in the working directory | B |
| `config.json` (B) in the global config dir, no `opencode.json` | B |
| `routing.json` (B) in the global config dir | none (file name ignored) |

## E4: precedence and coexistence (static, `probe-gen`)

| Setup | Resolved model |
|---|---|
| global `opencode.json` = A, project `opencode.json` = B | B |
| global `opencode.json` = A, `OPENCODE_CONFIG` = B | B |
| `opencode.json` (A, plus a permission probe rule) and `config.json` (B) | A, and the probe rule is present |
| `opencode.json` holds only the permission probe, `config.json` = B | B, and the probe rule is present |
| project `opencode.json` = A, global `config.json` = B | A |

No deprecation or legacy warning was printed for `config.json`.

Precedence, highest first: agent frontmatter, `OPENCODE_CONFIG`, project `opencode.json`, global `opencode.json`, global `config.json`. (F35, F36)

## Not tested

- `OPENCODE_CONFIG` against a project `opencode.json`.
- `config.json` at run time was not covered by E1 to E4. E5 covers it.
- Whether `config.json` is a legacy name that a later OpenCode stops reading. 1.19.3 prints no warning.
- A different OpenCode version. All results are 1.19.3 only.

## Reproduce

```bash
FH=/d/opencode-fake-home-exp; CFG=$FH/.config/opencode
HOME=$FH XDG_CONFIG_HOME=$FH/.config opencode debug agent probe-cfg | grep -A3 '^  "model": {'
HOME=$FH XDG_CONFIG_HOME=$FH/.config opencode run --agent boss --format json "Call the task tool once with subagent probe-none and prompt say probe. Then reply done"
grep -o '"parentSessionId":"[^"]*","sessionId":"[^"]*","model":{[^}]*}' <output>
```

## E5: routing through config.json alone (fake home, 2026-10-20)

Setup: a copy of `opencode.json`, `agents/` (15 agents, all `model:` lines deleted) and `execution/routing.json` as `config.json` in a fake home (`/d/opencode-fake-home-routing`). No `AGENTS.md`, hooks or skills, so the first-run gate (F8) cannot stop a headless agent.

| Step | Result |
|---|---|
| `validate_framework.py --resolved-models` with `config.json` | OpenCode resolved the profile's model for all 15 agents (the only issue was the unrelated `$schema` drift below) |
| Control: `config.json` removed | 15 issues, "no model resolved" (F34). The check detects a missing routing file |
| Runtime: `boss` (primary) routed to haiku, `probe-rt` (subagent) routed to gpt-5.4-mini, both with no `model:` line; `boss` delegates once through `task` | The child session recorded `gpt-5.4-mini`. A child that inherited its caller would have recorded haiku |

Caveat: the event stream listed only the child's `modelID`. The parent's model (haiku) rests on `opencode debug agent boss`.

Side finding: the first launch of OpenCode after `setup.py` linked `config.json` rewrote `execution/routing.json` through the link. The diff was one added line, `"$schema": "https://opencode.ai/config.json"`. A reproduction in a throwaway home (config.json without the line) showed the line being added as line 2. With the line already first, the file was left unchanged and the model still resolved. No model id changed.

## E6: running a real reviewer as a primary agent (fake home, 2026-10-22)

Setup: a fake home `/d/opencode-fake-home-capture` made of copies (no links) with two throwaway read-only agents without a `model:` line (`sample-reviewer`, primary; `sample-sub`, subagent), scratch repos `proj-a` to `proj-f`, and routing files that set haiku. Runs used `opencode run --format json` with the task and diff attached through `-f` (F10), OpenCode 1.19.3. The raw output of three runs is kept as fixtures in `tests/fixtures/opencode-run/`.

| Step | Result |
|---|---|
| `agent.<name>.mode: "primary"` in the `OPENCODE_CONFIG` file; `debug agent` for the throwaway subagent and for the real `code-reviewer` | both stayed `mode: subagent`: the entry is ignored (F37) |
| The same config, real run with `--agent sample-sub` | stderr warning "Falling back to default agent", exit 0; the export shows agent `build` on `gpt-6-astra`, not on the routed haiku (F37, F38) |
| Primary agent `sample-reviewer` routed to haiku, JSON report requested by an attached task file | exit 0 in 20 s; events `step_start`, `text`, `step_finish`; the reply was a valid report; no event names the model (F43) |
| `opencode export` of that session and of the fallback session | the assistant message records the agent and the model that ran (`sample-reviewer`, and `build` for the fallback); 4.3 to 5.6 s, 7.7 s cold, `--pure` no faster (F43, F44) |
| Routing file with a model id that does not exist | exit 1 in about 10 s, empty stderr, error events with the text in `error.data.message`; both repos unchanged (F42) |
| Project `.opencode/opencode.json` and project `opencode.json` that set an agent model; a project that sets none | the model resolved from both files; none for the project without one (F34, F41) |
| Project `.opencode/agents/<name>.md` with a `model:` line | beat the routing (sonnet over haiku), also with a config-dir copy present (F40) |
| `OPENCODE_CONFIG_DIR` with a same-name primary copy of the subagent, model from `OPENCODE_CONFIG` | `debug agent`: primary on haiku (without it: subagent). Real run: exit 0, empty stderr, export agent `sample-sub` on haiku (F39) |

Not tested: whether the global `opencode.json` permissions apply when `OPENCODE_CONFIG_DIR` is set (U4); which fields of a project agent file and a config-dir copy win one by one; other OpenCode versions.

## E7: the real code-reviewer through the runner (fake home, 2026-10-23)

Setup: `run_review` with a copy of `policy.json` and of `agents/code-reviewer.md`, a one-line profile that routes `code-reviewer` to haiku, and the scratch repo as target (it holds no `src/total.ts` and no `.ai-framework.json`). The patch was the sample diff of E6. The record went to the fake home, not to the repo. OpenCode 1.19.3.

| Step | Result |
|---|---|
| `debug agent code-reviewer` with the live global config, and with the per-run config folder and run config | `subagent` on gpt-5.6-terra, and `primary` on haiku. 140 permission rules each, the same set, the same order outside the skill folders (the skill rules are in a different order); `edit`, `write` and `task` end in deny in both (U4) |
| Run 1: the task file asks for JSON, the message says to follow it | execution success, artifact failure. The reply starts with `## Analysis` and ends with one fenced JSON block that passes the schema and the rules (REQUEST CHANGES, 2 BLOCKING). 101 s, 44k tokens, $0.040, seven tool calls that load skills (F11, F45) |
| Run 2: the task file and the message say that the whole reply is the JSON and that it overrides the agent's output format | execution success, artifact success: a bare JSON object (REQUEST CHANGES, 1 BLOCKING). 52 s, $0.022 (F45, F46) |
| Both runs | requested and resolved model were haiku, no fallback; no run folder left in the temp folder; the scratch repo stayed clean; the number of node processes was the same before and after |

Caveats: one model and one run each, so F45 says nothing about GPT or Gemini. Both reports cite line 8 of a file that does not exist in the target: validity is not correctness, and correctness is measured in the benchmark (step 2.3). A timeout with a child process was not tested.

## E8: the command line entry with the production model (2026-10-24)

Setup: `python -m execution.runner.cli --role code-reviewer` with the real profile (`gpt-5.6-terra`), once on the scratch repo (no `.ai-framework.json`) and once on a copy of it with `.ai-framework.json` and a `src/total.ts` that holds the loop bug of the E6 sample patch on line 3. OpenCode 1.19.3. The record went to `execution/runner/runs/`, which is not versioned.

| Step | Result |
|---|---|
| Target without `.ai-framework.json` | not run, exit 2, no model call; the message names the missing file (F14) |
| Ready target | exit 0; execution and artifact success; one BLOCKING finding; 110 s, $0.089; requested and resolved model equal; a bare JSON object (F47) |
| Line cited | line 8; the bug is on line 3 of the file, and line 8 of the sample patch is its added line (F48) |
| Both targets afterwards | the scratch repo unchanged; the copy holds only the two files added for the run |

Caveats: one run, one model, one diff. Gemini was not run. The line reading in F48 rests on three runs of the same patch.

## E9: reviewer benchmark, 63 runs (2026-10-24)

Setup: `python -m execution.runner.benchmark --models github-copilot/claude-haiku-4.5,github-copilot/claude-sonnet-5 --repeats 3`. The baseline is the production model of `code-reviewer` (`gpt-5.6-terra`). 7 cases (5 with a planted bug, 2 clean), the real `code-reviewer` prompt, the JSON-only task of F45. OpenCode 1.19.3. The result files are in `execution/runner/runs/`, which is not versioned, so the numbers are copied here.

| Model | Valid reports | Bugs found | False positives | Violations and fallbacks | Stable verdicts | Cost | Mean time |
|---|---|---|---|---|---|---|---|
| gpt-5.6-terra (baseline) | 21 of 21 | 15 of 15 | 0 of 6 | 0 | 7 of 7 | $1.578 | 47 s |
| claude-haiku-4.5 | 20 of 21 | 15 of 15 | 0 of 6 | 0 | 7 of 7 | $0.510 | 35 s |
| claude-sonnet-5 | 19 of 21 | 13 of 15 | 0 of 6 | 0 | 6 of 6 | $1.027 | 39 s |

| Run | What happened |
|---|---|
| sonnet `retry-swallows-error` #1 and #2 | artifact failure: the reply was prose; it called the task file an injected instruction (F50) |
| haiku `clean-guard-with-test` #3 | execution failure: stop reason tool-calls after a rejected `external_directory` request for the temp folder (F51) |

Line cited by the runs that found the bug: the patch line in 37 of 43, the file line in none, neither in 6 (F49).

Caveats: every model found every bug it produced a report for, so the cases do not rank the models. Two clean cases are weak evidence on false positives. No Gemini model was available.

## E10: reasoning effort as a variant, and the model list (fake home, 2026-10-25)

Setup: a fake home with one throwaway read-only agent `probe` (no `model:` line) routed to claude-haiku-4.5 through an `OPENCODE_CONFIG` file, three configs (no variant, `variant: high`, `variant: xhigh`), and `opencode models github-copilot --verbose`. OpenCode 1.19.3.

| Step | Result |
|---|---|
| Model list from the Copilot picker against `opencode models github-copilot` | the same 18 models; the policy lacked claude-haiku-5.5, claude-sonnet-5.5 and gpt-6.1-sol and listed six that are not offered (claude-opus-4.7, claude-opus-4.7-fast, gpt-5-mini, gpt-5.4, gpt-5.4-mini, gpt-5.5); every model the profile uses is offered |
| `--verbose` listing | each model has `variants`; most low, medium, high, xhigh, max; claude-haiku-4.5 only high and max; gpt-5.3-codex no max; five GPT models also none (F53) |
| `debug agent probe` with `variant: high`, and with `options.reasoningEffort: high` | both keys are accepted and shown; the `"invalid": true` line is the tool entry named `invalid`, present without any variant |
| Run with no variant, `high`, `xhigh` | exit 0, 3 events, empty stderr each. Export: session `info.model.variant` default, high, default; assistant `info.variant` only for high; reasoning tokens 0, 47, 0 (F52) |

Caveats: one model, one prompt. The `none` level and `options.reasoningEffort` were not run. Costs of the three runs are not comparable (cache state differed).

## E11: do allow patterns match chained commands (fake home, 2026-10-26)

Setup: a fake home with one throwaway agent whose bash rules were `"*": deny` and `"echo ok *": allow`, routed to claude-haiku-4.5, one headless run. The prompt was passed as an attached file because `&`, `|` and `>` break the Windows shim (F10). OpenCode 1.19.3.

| Call | Result |
|---|---|
| `echo ok one` | ran |
| `echo ok two; echo chained > chain-semicolon.txt` | denied by the rule, no file written |
| `echo ok three && echo chained > chain-and.txt` | denied by the rule, no file written |
| `echo ok four \| tee chain-pipe.txt` | denied by the rule, no file written |
| `echo other` | denied by the rule (control) |

Caveats: one model, one run, one pattern shape. Patterns with a `*` in the middle were not tested. The agent-level permission counts from the 3A pilot (42 `ask` hits in 12 sessions, mostly the Python test runners and `cd ... &&` chains) were computed with an approximate wildcard matcher whose denials all matched the real ones, so the `ask` counts are approximate.

## E12: candidate models on the reviewer benchmark (2026-10-26)

Setup: `python -m execution.runner.benchmark --trial --repeats 3`, run in the background with `< /dev/null` (F56). The baseline is the production model of `code-reviewer` (`gpt-5.6-terra`); the candidates are claude-haiku-5.5, claude-sonnet-5.5, gpt-6-luna and gpt-6.1-sol, which the policy lists as experimental and which count as approved inside the benchmark only. 7 cases, 3 repeats, 105 runs, the real `code-reviewer` prompt, the JSON-only task of F45. OpenCode 1.19.3. The result files are in `execution/runner/runs/`, which is not versioned, so the numbers are copied here. Earlier attempts failed or were interrupted and are not counted (F56).

| Model | Valid reports | Bugs found | False positives | Cost | File line / patch line cited |
|---|---|---|---|---|---|
| gpt-5.6-terra (baseline) | 20 of 21 | 14 of 15 | 0 of 6 | $0.476 | 4 / 9 |
| claude-haiku-5.5 | 20 of 21 | 14 of 15 | 0 of 6 | $0.068 | 14 / 0 |
| claude-sonnet-5.5 | 21 of 21 | 15 of 15 | 0 of 6 | $1.273 | 8 / 5 |
| gpt-6-luna | 18 of 21 | 7 of 15 | 5 of 6 | $0.126 | 0 / 7 |
| gpt-6.1-sol | 21 of 21 | 15 of 15 | 0 of 6 | $1.759 | 13 / 0 |

Invalid runs: baseline `retry-swallows-error` #1, haiku-5.5 `sql-string-concat` #1, luna `off-by-one-loop` #1 and `null-from-repository` #1 did not finish within 600 s after 1,114 to 16,288 s (F55); luna `retry-swallows-error` #2 stopped with stop reason tool-calls after 100 s. Without the four runs across a sleep, the baseline and haiku-5.5 are valid in 20 of 20 runs and found 14 of 14 bugs.

Per case for luna (F found, M missed, FP false positive, ok approved, x invalid): off-by-one x,F,F; leap-year F,F,M; retry M,x,M; null x,M,M; sql F,F,F; clean-rename FP,FP,FP; clean-guard FP,FP,ok (F57). The other four models had no M and no FP.

Luna reproduction on the two clean cases (a temporary bench root, one run each): `clean-rename-helper` gave REQUEST CHANGES with one BLOCKING STATIC ANALYSIS finding, because the static analysis could not find the changed files in the workspace; `clean-guard-with-test` ended with stop reason tool-calls and no reply.

Caveats: the timing columns are not usable (F55). Four models are close, so the cases screen out a bad model and do not rank the good ones; cost is the clearest difference. Two clean cases are weak evidence on false positives. The static-analysis message may mean that the precheck cannot analyse the benchmark targets for any model; this was not investigated. No Gemini model was available.

## E13: the framework's own flow on plan step 3A (pilots, 2026-10)

Setup: in a git worktree, `/task` implemented the `protected_paths` check of step 3A.2 and a fix for empty and dot paths; a second pilot step (leading-slash paths on Windows) ran later in the terminal UI. OpenCode 1.19.3 on the live global config. The first table comes from `opencode export` of the 12 sessions of the first pilot; the permission counts come from the bash rules resolved with `opencode debug agent` and an approximate wildcard matcher (its 12 denials all matched the real ones, so the `ask` counts are approximate).

| Agent | Sessions | Wall time | Tool time | Messages | Tokens | Reasoning tokens | Skill calls | Cost |
|---|---|---|---|---|---|---|---|---|
| orchestrator | 1 | 19,144 s | 2,677 s | 35 | 2,440,373 | 5,393 | 0 | $1.609 |
| backend | 5 | 1,633 s | 1,191 s | 64 | 1,934,910 | 2,695 | 0 | $0.881 |
| code-reviewer | 4 | 551 s | 559 s | 26 | 854,237 | 7,356 | 68 | $0.672 |
| qa | 1 | 208 s | 139 s | 6 | 138,729 | 2,719 | 4 | $0.242 |
| gatekeeper | 1 | 133 s | 66 s | 12 | 414,859 | 166 | 0 | $0.234 |

- Total cost about $3.64. The four child agents took 2,525 s together, which matches the orchestrator's 2,677 s of task calls; the rest of its 19,144 s was waiting (for people, permission prompts or a sleeping machine; the export cannot tell which).
- Reasoning tokens are under 1% of the tokens for every agent except qa (2%); almost all tokens are re-read context. Lowering the reasoning effort would save little.
- Slowest tool calls: six orchestrator `task` calls of 208 to 483 s; backend `python -m unittest` 145 s and `cd ... && python tools/validate_framework.py` 135 s. The validator takes 6 s directly, so most of the 135 s was probably a permission prompt (inferred).
- Bash calls in the first pilot: 102. backend 5 allow and 29 ask; code-reviewer 25 allow, 9 ask, 1 deny; qa 1 allow and 4 ask; gatekeeper 6 allow and 8 deny; orchestrator 8 allow and 6 deny. The orchestrator's and gatekeeper's denials are by design (deny-by-default). After PR 72 the Python test runners are allowed for backend and qa.
- Second pilot: the user approved six commands once (a `find` with a `python -c` fallback, a `grep` through bash, `python -m unittest tests.test_protected_paths`, `python tools/validate_framework.py`, a mistyped `python lizard` and `python -m lizard`); which agent asked is not recorded. The result: one commit of 5 changed lines in `protected_paths.py` and 10 test lines; 503 tests, validator green, lizard clean, only `execution/verification/` and `tests/` changed.

Test suite (F60): 82 s for 501 tests; seconds per module from the 600 slowest tests: quick_lane_check 20.0 (16 tests), git_context 10.7 (9), benchmark 10.2 (16), entry_points 6.5 (2), static_analysis 5.5 (5), bench_resume 5.4 (6).

Retest failures of 2026-10-25 (F58, F59): sonnet-5 `off-by-one-loop` #2 ended after an auto-rejected `echo done`; haiku-4.5 `clean-guard-with-test` #3 wrote prose before a fenced JSON block.

Caveats: one task, one repository, two pilots; the `ask` counts are approximate; waiting time cannot be split into prompts, thinking and sleep.

## E14: the working directory of a headless run (2026-11-08)

Setup: the first real `qa` run through `python -m execution.runner.cli --role qa` (a throwaway TypeScript fixture outside both repositories, `gpt-5.6-sol`), started from Git Bash in `/d/ai-framework`; then three probe runs of `claude-haiku-5.5` in a probe folder with the first-run files. OpenCode 1.19.3.

| Step | Result |
|---|---|
| The `qa` run | execution, artifact and workflow success, but `NEEDS_DEVELOPER` with no tests written. Its 16 tool calls read `D:\ai-framework\docs\project-overview\stack.md` (the framework's own, Python `unittest`), failed on `D:\ai-framework\src\slug.ts`, and ran five globs and four git commands against `D:\ai-framework`; no `write` call; the live repository stayed clean |
| `opencode export` of that session | `info.directory`, `cwd` and `root` all `D:\ai-framework`, not the temporary copy the runner started it in |
| Probe A, `PWD` inherited (`D:/ai-framework`) | session directory `D:\ai-framework` |
| Probe B, `PWD` removed | session directory `D:\qa-pwd-probe` |
| Probe C, `PWD` set to the probe folder | session directory `D:\qa-pwd-probe` |

Caveats: one model, one session each, Git Bash on Windows only. That the earlier reviewer runs (E9 to E13) worked in the framework repository is inferred, not checked. The export of a session started in a temporary folder is read by the runner before the folder is removed; whether `opencode export` finds such a session from another folder was not tested. The `qa` benchmark evidence will be E15.

## E15: qa write permission and out-of-folder reads (2026-11-09 and 2026-11-10)

Setup: `opencode debug agent qa` with a per-run `OPENCODE_CONFIG_DIR` (no model call) for four versions of `agents/qa.md`; four real `qa` runs through `python -m execution.runner.cli --role qa` on a throwaway TypeScript fixture (`gpt-5.6-sol`, `node --test`); two probe runs of `claude-haiku-5.5` with `external_directory` set to `ask` and to `deny`. OpenCode 1.19.3, `PWD` removed (F74).

| Step | Result |
|---|---|
| `debug agent`: `edit: deny` with `write: allow`, and `edit: deny` alone | the same rules; `apply_patch: false` in both |
| `edit` as a map with test paths, and `edit: allow` | `apply_patch: true` in both |
| Run 1 (after the PWD fix) | stop reason tool-calls; the last call was `apply_patch` through bash, auto-rejected |
| Run 2 (edit map) | stop reason tool-calls with no write; two reads of the skills folder (`external_directory`, `ask`) were auto-rejected |
| Probe `ask` against `deny` | `ask`: stop reason tool-calls, no reply; `deny`: the read failed, the model answered, stop reason stop |
| Run 3 (edit map and the project docs named in the task message) | `apply_patch` completed on `src/slug.test.ts`; execution, artifact and workflow success; 6 tests passed; the fixture stayed unchanged |

Caveats: one run per step; the probe used another model than `qa`; no production path was tempted; the Windows path match was seen for `src/slug.test.ts` only.

## E16: reviewer retest after the PWD fix, and the template read (2026-11-10 and 2026-11-11)

Setup: `python -m execution.runner.benchmark --trial --repeats 2 --models github-copilot/claude-haiku-5.5,github-copilot/gpt-6-luna`, started in the background on `main` (the baseline `gpt-5.6-terra` is added), 42 runs planned; then `opencode debug agent code-reviewer` with per-run config folders (no model call). OpenCode 1.19.3.

| Step | Result |
|---|---|
| Retest rows | 5 rows were written, then nothing for about 11 hours and no python, opencode or node process was left (cause unknown: a machine sleep or a closed terminal is possible). Baseline off-by-one-loop #1 and leap-year-century #1 failed, gpt-6-luna off-by-one-loop #1 failed, claude-haiku-5.5 found the bug in both of its runs with a valid report |
| The three failures | stop reason tool-calls, no reply, an auto-rejected `external_directory (D:\ai-framework\skills\project-overview\sub\*)`; the F74 guard rejected none |
| Skill output | the `project-overview` skill ends with a base directory line for `C:\Users\...\.config\opencode\skills\project-overview` and lists the `sub` files there; that folder is a link to `D:\ai-framework\skills` |
| Rule order, control | one `*` rule (`ask`) at position 0 and 92 allows after it |
| Rule order, blanket `external_directory: {"*": deny}` in the run config (top level or in the agent entry) | `deny *` at position 91 with 2 allows after it, so it overrides about 90 specific allows |
| Rule order, `*skills*project-overview*` deny | 94 rules, the first still `ask *`, one deny at position 91, then the reviewer's `linting-tools\references` allow and the `tool-output` allow |

Caveats: five rows only; no run with the deny yet; whether the `skill` tool still loads the skill under the rule is untested; the E9 to E13 numbers were not rerun.

## E17: reviewer retest after the headless deny (2026-11-13)

Setup: `python -m execution.runner.benchmark --models github-copilot/claude-haiku-5.5,github-copilot/gpt-6-luna --trial --repeats 2 --out /d/bench-retest-3`, run from the worktree of branch `fix/headless-ask-deny` (F78 applied), 42 runs; one baseline row that hit the timeout or a sleep was repeated with `--resume`. Then a manual `qa` run on the fixture `/d/qa-manual-fixture`. OpenCode 1.19.3, Windows, Git Bash. The result files are in `/d/bench-retest-3`, which is not versioned, so the numbers are copied here.

| Run | Valid | Bugs found | False positives | Auto-rejected | Cost | Mean time |
|---|---|---|---|---|---|---|
| bench-retest-2, `gpt-5.6-terra` (baseline) | 12 of 14 | 8 of 10 | 1 of 4 | 2 | not recorded here | not recorded here |
| bench-retest-2, `claude-haiku-5.5` | 13 of 14 | 9 of 10 | 0 of 4 | 0 | not recorded here | not recorded here |
| bench-retest-2, `gpt-6-luna` | 6 of 14 | 6 of 10 | 0 of 4 | 8 | not recorded here | not recorded here |
| bench-retest-3, `gpt-5.6-terra` (baseline) | 14 of 14 | 10 of 10 | 0 of 4 | 0 | $1.599 | 75 s |
| bench-retest-3, `claude-haiku-5.5` | 14 of 14 | 10 of 10 | 0 of 4 | 0 | $0.040 | 36 s |
| bench-retest-3, `gpt-6-luna` | 14 of 14 | 10 of 10 | 0 of 4 | 0 | $0.112 | 107 s |

| Step | Result |
|---|---|
| Terra on `clean-rename-helper`, 4 runs on `main` before F78 | 2 REQUEST CHANGES with one BLOCKING `API COMPATIBILITY` finding on `src/format.ts:1` (the exported `fmt` is renamed and no alias is kept), 2 APPROVED; static analysis found the changed files in all 4 |
| `qa` on `/d/qa-manual-fixture` with the changed agent copy | `TESTS_WRITTEN`, 1 test file, 6 tests; execution, artifact and workflow success; `node --test` exit 0 |

Caveats: two repeats per case, so the cases screen out a bad model and do not rank the good ones. The F78 effect rests on the auto-rejected count (10 of 42 before, 0 of 42 after). The terra rename result is ambiguous: the diff does not show whether `fmt` has outside callers, and the same case gave 2 of 4 flags in one batch and 0 of 4 in the other. Luna's E12 result did not reproduce, but F74, F77 and F78 changed in between, so the cause is unknown. The reviewer cannot run `jf` or other unlisted commands any more, so Xray is not part of this benchmark; whether it reports Xray as skipped was not checked in the retest-3 reports. `qa` was checked in one run, and the second step above ran before F78 for terra only. E9 to E13 were not rerun and predate F74, so their rankings are history.
