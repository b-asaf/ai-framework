# Model routing evidence (E1 to E4)

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
