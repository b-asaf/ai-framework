# DEC-019 - Model routing through a generated config.json

**Status:** Accepted. Supersedes parts of DEC-016: the `roles/` home, access intent with its translation to deny rules, and the generated `agents/*.md`.
**Date:** 2026-10-19

## Context

- DEC-016 planned a `roles/` layer (`roles/<role>.json` plus a prompt file), an adapter that translates `access: read-only` into deny rules, and `agents/*.md` generated from roles and a profile.
- The stated goal is "simple to use, no duplication". `roles/` would hold the same information as `agents/*.md`, and the access translation would be a second source of truth for permissions, which is where most real bugs were (F5, F20, F27, F28, F30).
- The original aim was to move the model out of the agent files. Experiments E1 to E4 (`tests/bench/model-routing-evidence.md`, OpenCode 1.19.3) showed how OpenCode resolves a model:
  - F32: a `model:` line in an agent file beats any config entry.
  - F33: an `agent.<name>.model` config entry applies to an agent file with no `model:` line.
  - F34: an agent with no model anywhere runs on its caller's model. A `plan-reviewer` missing from the routing would share the planner's model, which is the DEC-014 incident.
  - F35: precedence, highest first: agent frontmatter, `OPENCODE_CONFIG`, project `opencode.json`, global `opencode.json`, global `config.json`.
  - F36: a global `config.json` is read next to `opencode.json`. No warning in 1.19.3, but the name may be a legacy one.
- DEC-016 cites the reviewer spike (F12) as proof that a model swap needs only a profile change. The spike code is not in the repository, so that claim is evidence from an earlier run and not reproduced. Phase 2 reproduces it.

## Options considered

- **Option A: keep the DEC-016 design.** `roles/`, generated `agents/*.md`, access translation. More files, a second source of truth for permissions, and a generated agents folder or committed mirror.
- **Option B: committed `agents/*.md` with a generated `model:` line.** No link change, but the model sits in two places (profile and agent files) and the files can drift.
- **Option C: keep `model:` in the agent files and the matrix.** The state before DEC-014. Rejected.
- **Option D: write routing into the hand-written `opencode.json`.** It already carries permissions and is linked into the config. It would mix generated and hand-written content.
- **Option E: agent files without a model, a profile as the only routing, rendered into a generated `execution/routing.json` that `setup.py` links as `config.json`.** Chosen.
- Setting `OPENCODE_CONFIG` for every launch was rejected as the normal path. It needs an environment variable for every OpenCode launch on every machine. It stays as the benchmark mechanism.

## Decision

- `agents/*.md` hold responsibility, prompt and permissions, and no `model:` line.
- `execution/profiles/default.json` is the only place that maps an agent to a model. An optional `capability` note per entry is documentation only, and no code reads it.
- `tools/generate_routing.py` renders the profile into `execution/routing.json` (`{"agent": {"<name>": {"model": "<id>"}}}`). The file is committed. `setup.py` links it as `~/.config/opencode/config.json`.
- The validator fails on:
  - a `model:` line in an agent file,
  - an `agent.*.model` entry in the repo's `opencode.json`,
  - an agent without a profile entry, or an entry without an agent,
  - drift between `routing.json` and the profile,
  - a resolved model from `opencode debug agent <name>` that differs from the profile (no model call).
- No per-project model overrides (decision #4, option A): the validator and, from Phase 2, the runner preflight flag `agent.*.model` in a project `opencode.json` and in a file named by `OPENCODE_CONFIG`. The runner's own benchmark routing is the only allowed use of `OPENCODE_CONFIG`.
- Constraints are checked against the profile: independence and experimental status (`policy.json`, steps 1.4 and 1.6).
- `roles/` and the access-to-deny translation are dropped. Read-only is enforced by the validator rules of step 1.5, not by a second source of truth.
- `MODEL-ASSIGNMENT-MATRIX.md` becomes a view generated from policy and profile, or a printed view (step 4.3).
- The runner and verification code live under `execution/runner/` and `execution/verification/` (decision #7).

**Still valid from DEC-016:** the `models` and `constraints` shape of `policy.json`, families independent of provider, contracts in `execution/schemas/` with artifact ownership, the three success levels, the `RunRecord` fields, and the provider boundary (the `roles/` part is replaced by "`execution/verification/` and the schemas contain no model ids or provider names").

**Touches:** `agents/*.md`, `execution/`, `tools/validate_framework.py`, `tools/generate_routing.py`, `setup.py`, `docs/decisions/MODEL-ASSIGNMENT-MATRIX.md`.

## Reasoning

1. **Agent or deterministic?** Deterministic. Which model an agent gets, and whether it is legal, is data checked in code. The check on the resolved model needs no LLM and no model call.
2. **Trade-offs.** Less structure than DEC-016 and no second source of truth for permissions. In return the file name `config.json` is a dependency on undocumented behavior (F36), and OpenCode precedence (F35) means a leftover `model:` line or a project file silently wins. Both are covered by validator checks on the resolved result, which would fail loudly if a later version stops reading `config.json`.
3. **Cheaper way?** Keeping `model:` in the agent files and checking independence in the validator (Phase 1 already does this). It leaves the model in the agent file, which was the trigger for this change.
4. **What a developer can now see or do.** Change a role's model by editing one profile entry and running the generator. See in `--verify` whether the model OpenCode resolves is the profile's model. Get an error when an agent has no profile entry, instead of a silent run on the caller's model.

## Consequences

- A new role touches 2 files (`agents/x.md` and a profile entry), not the 3 files of DEC-016.
- Live-merge hazard: after the pull of Phase 1b, agent files have no model until `python setup.py` has linked `config.json`. Run `python setup.py` right after the pull. `--verify` fails and names the missing link.
- `config.json` at run time was not tested by E1 to E4 (they used `opencode.json`). Step 1b.5 tests it in a fake home before merging.
- The benchmark swap uses `OPENCODE_CONFIG` with a generated bench profile. No edit to agent files and no derived copy.
- All results are for OpenCode 1.19.3. Re-run the resolved-model check when OpenCode is upgraded.
- `docs/transition-plan.md` already reflects this decision (PR #49).
- Evidence: `tests/bench/model-routing-evidence.md`, findings F32 to F36, and F12 (unreproduced) in `docs/transition-plan.md`.
