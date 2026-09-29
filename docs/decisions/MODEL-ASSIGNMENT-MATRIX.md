# Model Assignment Matrix

**Status:** Accepted
**Decision:** DEC-011, amended by DEC-014
**Purpose:** Canonical mapping between framework agents, model assignments, model families, responsibilities, and validation relationships.

**Last verified against the available model list:** 2026-09-29

## 1. Model catalog

The framework uses a closed model list. An agent may only be assigned a model that exists in the approved/available model catalog.

| Model | Family | Tier | Intended use |
|---|---|---|---|
| `opencode/ling-3.0-flash-fin-free` | OpenCode | Free/experimental | Reserved; evaluate before critical assignment |
| `opencode/longcat-2.5-preview-free` | OpenCode | Free/experimental | Reserved; evaluate before critical assignment |
| `opencode/mimo-v2.6-flash-free` | OpenCode | Free/experimental | Reserved; evaluate before critical assignment |
| `opencode/muse-spark-1.3-contributor-free` | OpenCode | Free/experimental | Reserved; evaluate before critical assignment |
| `opencode/nemotron-3-ultra-free` | OpenCode | Free/experimental | Reserved; evaluate before critical assignment |
| `opencode/nemotron-3.5-lightning-free` | OpenCode | Free/experimental | Reserved; evaluate before critical assignment |
| `opencode/space-bunny-free` | OpenCode | Free/experimental | Reserved; evaluate before critical assignment |
| `opencode/big-pickle` | OpenCode | Unclassified | New in the live list as of 2026-09-29; not yet evaluated — do not assign (section 7) |
| `github-copilot/claude-fable-5` | Claude | Frontier/experimental | Available; evaluate before default assignment |
| `github-copilot/claude-fable-5.1` | Claude | Frontier/experimental | Available; evaluate before default assignment |
| `github-copilot/claude-haiku-4.5` | Claude | Efficient | Lightweight support tasks |
| `github-copilot/claude-opus-4.7` | Claude | Frontier | Available alternative |
| `github-copilot/claude-opus-4.7-fast` | Claude | Frontier/fast | Available alternative |
| `github-copilot/claude-opus-4.8` | Claude | Frontier | Available alternative |
| `github-copilot/claude-opus-4.8-fast` | Claude | Frontier/fast | Available alternative |
| `github-copilot/claude-opus-5` | Claude | Frontier | Available alternative |
| `github-copilot/claude-opus-5.5` | Claude | Frontier | Independent planning/review validation |
| `github-copilot/claude-sonnet-5` | Claude | Strong general | Requirements, orchestration, implementation, final gate |
| `github-copilot/gpt-5-mini` | GPT | Efficient | Available alternative |
| `github-copilot/gpt-5.3-codex` | GPT | Coding-specialized | Available alternative; evaluate for coding-specific tasks |
| `github-copilot/gpt-5.4` | GPT | Strong | Available alternative |
| `github-copilot/gpt-5.4-mini` | GPT | Efficient | Available alternative |
| `github-copilot/gpt-5.5` | GPT | Strong | Available alternative |
| `github-copilot/gpt-5.6-luna` | GPT | Efficient | Available alternative |
| `github-copilot/gpt-5.6-sol` | GPT | Frontier/strong reasoning | QA / deep validation |
| `github-copilot/gpt-5.6-terra` | GPT | Strong | Implementation review |
| `github-copilot/gpt-6-astra` | GPT | Frontier/agentic | Architecture and long-horizon planning |
| `github-copilot/gpt-6-luna` | GPT | Efficient | Available alternative |
| `github-copilot/gpt-6-sol` | GPT | Frontier/agentic | Available alternative; evaluate before default assignment |

**Family rule:** `anthropic/claude-*` and `github-copilot/claude-*` are both Claude family. Provider prefix alone does not establish independence.

**Note on this catalog vs the live list:** this table is the framework's own *approved subset* — a deliberate curation, not a live mirror of whatever the Copilot entitlement happens to expose on a given day. A separate validation step (see section 8) checks assignments against both this table and the actual live `opencode models` output, since those two can drift independently (a model can vanish from this table by deliberate framework decision, or vanish from the live list by an entitlement/IT change outside the framework's control). `opencode/big-pickle` is the current example of the reverse: a model that appeared live since the last check but has not yet been evaluated or added here (see section 7 — new live models are never auto-adopted).

## 2. Agent-to-model assignment

| Agent | Assigned model | Family | Responsibility | Rationale |
|---|---|---|---|---|
| `architect` | `github-copilot/gpt-6-astra` | GPT | Architecture/HLD and atomic PR breakdown | Long-horizon planning and architectural reasoning |
| `plan-reviewer` | `github-copilot/claude-opus-5.5` | Claude | Independent plan validation | Cross-family, deep review of architecture/plans |
| `refactor-planner` | `github-copilot/gpt-6-astra` | GPT | Complex refactoring plan | Long-horizon reasoning over broad codebase changes; same model as `architect` — both are planning agents validated by `plan-reviewer` |
| `product-manager` | `github-copilot/claude-sonnet-5` | Claude | Interactive specification gathering | Strong reasoning at lower cost |
| `orchestrator` | `github-copilot/claude-sonnet-5` | Claude | Coordinates execution and scope | Coordination does not require frontier model |
| `api` | `github-copilot/claude-sonnet-5` | Claude | API implementation | Strong implementation |
| `backend` | `github-copilot/claude-sonnet-5` | Claude | Backend implementation | Strong implementation |
| `db` | `github-copilot/claude-sonnet-5` | Claude | Persistence/database implementation | Strong implementation |
| `frontend` | `github-copilot/claude-sonnet-5` | Claude | Frontend implementation | Strong implementation |
| `frontend-error-fixer` | `github-copilot/claude-sonnet-5` | Claude | Frontend debugging | Strong debugging |
| `ui` | `github-copilot/claude-sonnet-5` | Claude | UI implementation | Strong implementation |
| `code-reviewer` | `github-copilot/gpt-5.6-terra` | GPT | Implementation review | Cross-family from Claude implementation agents; non-experimental strong-tier model (see DEC-014 — replaces the unapproved `gpt-6-sol` default) |
| `qa` | `github-copilot/gpt-5.6-sol` | GPT | Tests/implementation validation | Cross-family deep validation |
| `gatekeeper` | `github-copilot/claude-sonnet-5` | Claude | Final gate before handoff | Independent from GPT validation; upgraded from `claude-haiku-4.5` (see DEC-014) now that a PASS triggers an automatic push and draft PR/MR with no human approval step before it |
| `web-research-specialist` | `github-copilot/claude-haiku-4.5` | Claude | Research support | Low-cost support |

## 3. Validation boundaries

Cross-family independence is required where an agent validates or materially challenges another agent's output.

| Producer | Validator | Required | Producer family | Validator family |
|---|---|---:|---|---|
| `architect` | `plan-reviewer` | YES | GPT | Claude |
| `refactor-planner` | `plan-reviewer` | YES | GPT | Claude |
| `api` | `code-reviewer` | YES | Claude | GPT |
| `backend` | `code-reviewer` | YES | Claude | GPT |
| `db` | `code-reviewer` | YES | Claude | GPT |
| `frontend` | `code-reviewer` | YES | Claude | GPT |
| `frontend-error-fixer` | `code-reviewer` | YES | Claude | GPT |
| `ui` | `code-reviewer` | YES | Claude | GPT |
| `api` | `qa` | YES | Claude | GPT |
| `backend` | `qa` | YES | Claude | GPT |
| `db` | `qa` | YES | Claude | GPT |
| `frontend` | `qa` | YES | Claude | GPT |
| `frontend-error-fixer` | `qa` | YES | Claude | GPT |
| `ui` | `qa` | YES | Claude | GPT |
| `code-reviewer` | `gatekeeper` | YES | GPT | Claude |
| `qa` | `gatekeeper` | YES | GPT | Claude |

## 4. Relationships without mandatory cross-family validation

| Relationship | Requirement | Reason |
|---|---:|---|
| `product-manager` → `architect` | No | Requirements are input, not independent validation |
| `orchestrator` → implementer | No | Coordination is not validation |
| `web-research-specialist` → `architect` | No | Research is supporting evidence |
| `architect` → `orchestrator` | No | Executing an approved plan is not validation |

## 5. Deterministic validation

The framework must validate:

1. Every referenced agent exists.
2. Every assigned model exists in the closed model catalog (section 1).
3. Every assigned model also exists in the live `opencode models` output at validation time.
4. Every model has an explicit family.
5. Every agent has exactly one effective model.
6. Every required validation edge exists.
7. Every cross-family edge has different families.
8. Provider differences do not count when the underlying family is the same.
9. Invalid assignments fail configuration validation; no silent substitution.
10. Agents do not dynamically choose their own model.
11. Model/validation configuration changes are explicit and reviewable.

`tools/validate_agents.py` currently covers 1, 2, 4, 5, 6, 7, 8. It reads this
file's section 1 table as the catalog. It does **not** yet check item 3 (the
live `opencode models` output) — that gap is exactly what let DEC-011's
`claude-sonnet-4.6` drift go undetected until a headless run failed. Still an
open follow-up.

## 6. Important distinction

**Model tier is not model independence.**

Track separately:

- **Provider** — who exposes the model.
- **Family** — used for independence checks.
- **Model** — exact identifier.
- **Tier/capability** — capability/cost classification.

Cross-family validation uses **family**.

Capability and cost decisions use **model/tier**.

## 7. Experimental models

Available models not in the default assignment should be evaluated deliberately rather than assigned opportunistically.

Examples:

- `opencode/*` free models, and `opencode/big-pickle`
- `github-copilot/claude-fable-5`
- `github-copilot/claude-fable-5.1`
- `github-copilot/gpt-5.3-codex`
- `github-copilot/gpt-6-sol`

A model enters the default assignment only after explicit evaluation/approval,
logged as its own DEC. (`gpt-6-sol` was briefly assigned to `code-reviewer`
without that record — DEC-014 reverts it to this experimental list and moves
`code-reviewer` to `gpt-5.6-terra`, which was already non-experimental.)

## 8. Keeping this in sync with the live model list

This table can drift from reality in two independent ways: (a) the framework
deliberately changes what it approves, or (b) the live Copilot entitlement
changes underneath the framework (model deprecated, renamed, access
revoked). A deterministic validation script (see DEC-011) checks live
`opencode models` output against both this table and every agent's actual
frontmatter assignment, once per session/task start. New models appearing
live never get auto-adopted (section 7 policy). An assigned model
disappearing live fails validation loudly, naming the affected agent(s);
the replacement is a human decision, logged as its own DEC.