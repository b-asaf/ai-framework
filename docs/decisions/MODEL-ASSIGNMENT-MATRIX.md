# Model Assignment Matrix

**Status:** Proposed
**Decision:** DEC-011
**Purpose:** Canonical mapping between framework agents, model assignments, model families, responsibilities, and validation relationships.

**Last verified against live `opencode models` output:** 2026-08-30

## 1. Model catalog

The framework uses a closed model list. An agent may only be assigned a model that exists in the approved/available model catalog.

| Model | Family | Tier | Intended use |
|---|---|---|---|
| `github-copilot/claude-opus-4.8` | Claude | Frontier | Architecture, complex planning (default) |
| `github-copilot/gpt-5.4` | GPT | Frontier | Independent validation, code review |
| `github-copilot/gpt-5.4-mini` | GPT | Efficient | QA / repeated validation |
| `github-copilot/claude-sonnet-5` | Claude | Strong general | Requirements, orchestration, implementation (default) |
| `github-copilot/claude-haiku-4.5` | Claude | Efficient | Low-cost support / gatekeeping |
| `github-copilot/gpt-5.3-codex` | GPT | Coding-specialized | Candidate for implementation/review experiments |
| `github-copilot/claude-opus-4.5` | Claude | Frontier | Available alternative; not default |
| `github-copilot/claude-opus-4.6` | Claude | Frontier | Available alternative; not default |
| `github-copilot/claude-opus-4.6-fast` | Claude | Frontier/fast | Available alternative; not default |
| `github-copilot/claude-opus-4.7` | Claude | Frontier | Available alternative; not default |
| `github-copilot/claude-opus-4.7-fast` | Claude | Frontier/fast | Available alternative; not default |
| `github-copilot/claude-opus-4.8-fast` | Claude | Frontier/fast | Available alternative; not default |
| `github-copilot/claude-opus-5` | Claude | Frontier | Available alternative; not default |
| `github-copilot/claude-sonnet-4.5` | Claude | Strong general | Available alternative; not default |
| `github-copilot/claude-sonnet-5` | Claude | Strong general | Available alternative; not default |
| `github-copilot/gpt-5-mini` | GPT | Efficient | Available alternative; not default |
| `github-copilot/gpt-5.6-luna` | GPT | Advanced | Available alternative; not default |
| `github-copilot/gpt-5.6-sol` | GPT | Advanced | Available alternative; not default |
| `github-copilot/gpt-5.6-terra` | GPT | Advanced | Available alternative; not default |
| `opencode/big-pickle` | OpenCode | Free | Reserved: low-stakes agents only, not currently assigned |
| `opencode/ling-3.0-flash-fin-free` | OpenCode | Free | Reserved: low-stakes agents only, not currently assigned |
| `opencode/mimo-v2.5-free` | OpenCode | Free | Reserved: low-stakes agents only, not currently assigned |
| `opencode/muse-spark-1.2-contributor-free` | OpenCode | Free | Reserved: low-stakes agents only, not currently assigned |
| `opencode/nemotron-3-ultra-free` | OpenCode | Free | Reserved: low-stakes agents only, not currently assigned |
| `opencode/nemotron-3.5-lightning-free` | OpenCode | Free | Reserved: low-stakes agents only, not currently assigned |

**Family rule:** `anthropic/claude-*` and `github-copilot/claude-*` are both Claude family. Provider prefix alone does not establish independence.

**Note on this catalog vs the live list:** this table is the framework's own *approved subset* — a deliberate curation, not a live mirror of whatever the Copilot entitlement happens to expose on a given day. A separate validation step (see section 8) checks assignments against both this table and the actual live `opencode models` output, since those two can drift independently (a model can vanish from this table by deliberate framework decision, or vanish from the live list by an entitlement/IT change outside the framework's control).

## 2. Agent-to-model assignment

| Agent | Assigned model | Family | Responsibility | Rationale |
|---|---|---|---|---|
| `architect` | `github-copilot/claude-opus-4.8` | Claude | Architecture/HLD and atomic PR breakdown | Highest planning/reasoning requirement |
| `plan-reviewer` | `github-copilot/gpt-5.4` | GPT | Independent plan validation | Must be independent from architect |
| `refactor-planner` | `github-copilot/claude-opus-4.8` | Claude | Complex refactoring plan | High reasoning requirement |
| `product-manager` | `github-copilot/claude-sonnet-5` | Claude | Interactive specification gathering | Strong reasoning at lower cost |
| `orchestrator` | `github-copilot/claude-sonnet-5` | Claude | Coordinates execution and scope | Coordination does not require frontier model |
| `api` | `github-copilot/claude-sonnet-5` | Claude | API implementation | Strong implementation |
| `backend` | `github-copilot/claude-sonnet-5` | Claude | Backend implementation | Strong implementation |
| `db` | `github-copilot/claude-sonnet-5` | Claude | Persistence/database implementation | Strong implementation |
| `frontend` | `github-copilot/claude-sonnet-5` | Claude | Frontend implementation | Strong implementation |
| `frontend-error-fixer` | `github-copilot/claude-sonnet-5` | Claude | Frontend debugging | Strong debugging |
| `ui` | `github-copilot/claude-sonnet-5` | Claude | UI implementation | Strong implementation |
| `code-reviewer` | `github-copilot/gpt-5.4` | GPT | Implementation review | Must be independent from implementers |
| `qa` | `github-copilot/gpt-5.4-mini` | GPT | Tests/implementation validation | Independent family at implementation boundary, lower cost |
| `gatekeeper` | `github-copilot/claude-haiku-4.5` | Claude | Final gate before merge | Independent from GPT validation |
| `web-research-specialist` | `github-copilot/claude-haiku-4.5` | Claude | Research support | Low-cost support; free-tier models remain reserved (section 7) rather than applied here — haiku is already cheap and reliably real |

## 3. Validation boundaries

Cross-family independence is required where an agent validates or materially challenges another agent's output.

| Producer | Validator | Required | Producer family | Validator family |
|---|---|---:|---|---|
| `architect` | `plan-reviewer` | YES | Claude | GPT |
| `refactor-planner` | `plan-reviewer` | YES | Claude | GPT |
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

- `github-copilot/gpt-5.3-codex`
- `github-copilot/gpt-5.6-luna`
- `github-copilot/gpt-5.6-sol`
- `github-copilot/gpt-5.6-terra`
- `github-copilot/claude-opus-4.8-fast`
- `opencode/*`

A model enters the default assignment only after explicit evaluation/approval.

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
