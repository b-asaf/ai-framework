# Session Summary — ai-framework Upgrade
> Key decisions and outcomes. Load this at the start of a new session to restore context.
> Keep this file updated as new sessions add changes.

---

## What this framework is

An agentic development framework wired into every major AI coding tool via symlinks.
Single source of truth for instructions, skills, agents, and workflow rules.
Goal: agile vertical PRs, no broken changes, no risky git actions without approval.

---

## Supported tools (after this session)

| Tool | Wired to |
|---|---|
| Claude Code | `~/.claude/CLAUDE.md` + skills + agents |
| OpenCode | `~/.config/opencode/AGENTS.md` |
| Codex CLI | `~/.codex/AGENTS.md` |
| Gemini CLI | `~/.gemini/GEMINI.md` |
| Cursor | `~/.cursor/rules/shared.mdc` |
| Windsurf | `~/.codeium/windsurf/memories/global-rules.md` |
| VS Code Copilot | `.github/copilot-instructions.md` (project-level) |
| Copilot IntelliJ | `%LOCALAPPDATA%/github-copilot/intellij/` (Windows) |

---

## Structure decisions

### `instructions/` — global rules, loaded every session
- `SHARED.md` — rules only (~95 lines). Checks 1+2, 10 non-negotiable rules. Trimmed from 159 lines.
- `SHARED-reference.md` — agent roles, task flow, skill routing. Loaded on-demand by orchestrator only.
- `CLAUDE.md`, `GEMINI.md`, `COPILOT.md`, `CURSOR.md`, `WINDSURF.md`, `VSCODE.md`, `GIT_COMMIT.md`

### `.opencode/` — tool-specific config and content
- `agents/` — 16 agent definitions
- `skills/` — 36 skill folders + `skill-routing/skill-rules.json`
- `verification/scripts/` — git hooks (install via `python setup.py --project`)

### Key structural rules
- `[XXX]` in `project-overview` = first-run not done. Never remove until first-run populates them.
- `project-overview/SKILL.md` is a thin entrypoint. Agents load sub-files selectively:
  - `sub/stack.md` — every agent, every task
  - `sub/patterns.md` — implementation agents + reviewers
  - `sub/topology.md` — orchestrator + architect only
  - `sub/tooling.md` — linter + first-run only
  - `sub/localization.md` — only when UI text is involved
- `SHARED-reference.md` is NOT loaded globally. Orchestrator loads it at task start only.

---

## Agent roster (16 total)

| Agent | Type | Added/modified |
|---|---|---|
| orchestrator | Primary | Modified: plan-reviewer step, refactor-planner routing, skill-rules.json load |
| product-manager | Primary | Unchanged |
| architect | Primary | Unchanged |
| plan-reviewer | Primary | New — validates HLD before any implementation |
| refactor-planner | Primary | New — safe incremental refactor plans |
| backend | Subagent | Unchanged |
| frontend | Subagent | Unchanged |
| ui | Subagent | Unchanged |
| db | Subagent | Unchanged |
| api | Subagent | Unchanged |
| linter | Subagent | Modified: static-code-analysis step 3 in run order |
| code-reviewer | Subagent | Modified: BLOCKING/NON-BLOCKING model, static-analysis precheck |
| qa | Subagent | Unchanged |
| gatekeeper | Subagent | Unchanged |
| frontend-error-fixer | Subagent | New — JS/TS build and runtime errors |
| web-research-specialist | Subagent | New — 3rd-party research before implementation |

---

## Skill roster (36 folders)

### New skills added this session
| Skill | Purpose |
|---|---|
| `clean-code-naming` | Naming rules + units-in-numeric-names (BLOCKING) |
| `clean-code-functions` | Small, single-purpose, CQS, max 3 params |
| `clean-code-comments` | When comments are justified vs renamed away |
| `clean-code-classes` | Cohesion, magic numbers, negative conditionals |
| `clean-code-solid` | Full SOLID with cite formats — replaces references/solid.md |
| `clean-code-error-handling` | Exceptions not codes, no null returns on failure |
| `clean-code-tests` | F.I.R.S.T., AAA, test outcomes not implementation |
| `clean-code-security` | OWASP Top 10 — all findings BLOCKING |
| `readability-cognitive-load` | 8 dimensions: nesting, boolean complexity, surprise factor |
| `static-code-analysis` | lizard (CCN≤10) + jscpd (dup≤10%), scoped to changed lines |
| `excalidraw-sequence-diagram` | Excalidraw JSON methodology, project-specific stripped |
| `skill-routing/skill-rules.json` | Machine-readable routing table, 14 rules |

### Skills modified this session
| Skill | Change |
|---|---|
| `code-standards` | Rewritten as entrypoint; links to clean-code-* skills; semantic duplication; BLOCKING/NON-BLOCKING model |
| `grill-me` | Domain model hygiene + ADR gate (3-criteria: hard to reverse, surprising, real trade-off) |
| `documentation` | Architecture JSON+SVG section; Strunk 5 writing rules |
| `atomic-changes` | 3 micro-slice rules: one behaviour, independent verifiability, never layer-based |
| `improve-codebase-architecture` | Screaming Architecture + Swap Test sections |
| `localization` | Full CSS and layout section: logical properties, direction on html, RTL icons, typography, Tailwind equivalents |
| `agent-guidelines` | skill-rules.json routing instruction; context budget trigger (8 responses / ~3k tokens) |
| `project-overview` | Split into thin entrypoint + 5 sub-files |

### Reference files — keep all except one
| File | Status |
|---|---|
| `code-standards/references/solid.md` | **DELETED** — superseded by clean-code-solid |
| `code-standards/references/kiss-yagni.md` | Keep |
| All other references/ files | Keep |

---

## Key rules to remember

**Git:** agents may run status/log/diff/branch and `git checkout -b` (after confirmation only).
Never commit, push, merge, rebase, reset.

**Branch:** agent proposes name → developer confirms → agent creates → then files are written.

**Severity model:** BLOCKING = rejects PR. NON-BLOCKING = advisory only.
SOLID violations, security issues, swallowed exceptions, missing units in numeric names = always BLOCKING.

**Context budget:** > 8 agent responses OR > ~3k token response → load `handoff`, compact session.

**skill-rules.json:** orchestrator reads this at task start. 14 rules with keywords + intentPatterns.
critical + high priority skills load automatically.

**SHARED.md is ~95 lines.** It only has checks and rules.
Agent roles and routing live in SHARED-reference.md — loaded on-demand.

---

## Files to delete from repo (if not already done)
- `.opencode/skills/code-standards/references/solid.md` (superseded by clean-code-solid)
- `AGENTS.md` at repo root (superseded by instructions/SHARED.md)
- `install.sh` at repo root (superseded by setup.py)

## File to rename (if not already done)
- `.opencode/skills/improve-codebase-architecture/SKILL .md` → `SKILL.md` (space in filename)

---

## Session 2 additions

### New constraints added
- **No MCP** — Rule 11 in SHARED.md. No MCP servers, connectors, or external tool integrations.
- **Isolated environment** — Rule 12 in SHARED.md. No HTTP/API calls, no writes outside repo.

### Prompt engineering improvements
- SHARED.md now uses XML tags (`<checks>`, `<rules>`, `<rule id="...">`) for reliable parsing across all LLMs
- Added Check 3 (`<investigate_before_answering>`) — Anthropic's exact anti-hallucination wording
- Rule 10 (surgical changes) extended with Anthropic's over-engineering guidance
- Agent-guidelines `investigate_before_answering` block added with XML wrapper

### RTK integration
- RTK = token reduction proxy. Intercepts shell tool calls, filters output, up to 90% fewer tokens.
- No MCP. Uses native agent hooks (PreToolUse for Claude Code, BeforeTool for Gemini, etc.).
- `setup.py --rtk` runs `rtk init` for each detected tool.
- Codex (prompt-level tier): RTK block is in `instructions/wrappers/codex-AGENTS.md`.
- RTK detection added to `_detect_installed_tools()`.

### Wiring changes
- Codex and OpenCode now wire **wrapper files** (not direct SHARED.md symlinks).
  Wrappers use `@import` syntax so RTK can append its block without breaking links.
- Gemini CLI now wires `~/.gemini/skills/` → `.opencode/skills/` for native skill discovery.
- GEMINI.md rewritten as thin wrapper using `@./SHARED.md` import.

### Provider prompt guideline findings
**Claude (Anthropic):** XML tags improve parse reliability. `<investigate_before_answering>` reduces hallucinations. Avoid over-engineering in surgical changes.
**Codex (OpenAI):** AGENTS.md is correct. `skills:` block in AGENTS.md enables skill routing. Wrapper files survive RTK appends.
**Gemini (Google):** `@import` syntax in GEMINI.md imports SHARED.md. Native skill discovery under `~/.gemini/skills/`. Hierarchical GEMINI.md loading — global + project-level.

---

## Session 3 additions — caching & memory

### Context ordering for prompt caching (agent-guidelines)
Added `<context_ordering>` block. Assembly order is now mandatory:
1. SHARED.md / SHARED-reference.md (rules)
2. Skill content (.opencode/skills/*/SKILL.md)
3. Agent definition (.opencode/agents/<agent>.md)
4. project-overview/sub/*.md (project-specific)
5. Task description and conversation

Steps 1-3 are identical across all sessions and all projects — stable cached prefix,
~90% discount on cache hits. Project-specific content (step 4) must never precede
framework content, or it breaks the cache for the entire framework block.

### Gatekeeper — memory persistence step (new, runs last)
Gatekeeper now checks for newly discovered patterns/conventions/facts not yet in
`project-overview/sub/*.md`. Gatekeeper is read-only — it reports proposed updates
to the orchestrator, which performs the write. Output format gained a
"project-overview updates" section. This makes project-overview compound across
sessions instead of being re-derived every time.

### Handoff — dual output
`handoff` skill now produces two outputs:
1. Detailed handoff doc (`.handoff-[task-slug]-[date].md`) — for the next message
2. Short dated entry in `docs/session-summary.md` (5-10 lines: what changed,
   decisions, pending) — for any future session

If a previous "Pending" entry was resolved this session, update it rather than
leaving it stale.

### Net effect
- #1 (ordering) + #4 (skill-before-project): zero saving alone, but the *enabler*
  for cache hits to apply to the framework's static content across all projects.
- #2 (gatekeeper memory): trades recurring re-derivation cost for one-time write +
  cached read. Compounds with project age.
- #3 (handoff dual-output): reduces next-session startup cost (avoids re-explaining
  context). Token-neutral this session.
- Skipped #5 (skill-overrides.json) — marginal value, added complexity, not worth it.
