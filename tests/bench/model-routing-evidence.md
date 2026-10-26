# Model routing evidence (E1 to E10)

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
