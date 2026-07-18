# Session Summary — ai-framework
> Current state of the framework. Load this at the start of a new session to restore context.
> Updated automatically by the `handoff` skill at session end.

---

## What this framework is

An agentic development framework wired globally into every AI coding tool via symlinks.
Run `python setup.py` once on any machine. Open any project folder in OpenCode (or any
supported tool) — the framework is active. No per-project setup needed.

Goal: agile vertical PRs, no broken changes, no risky git actions without developer approval.
Stack focus: Java/Spring Boot (BE), JavaScript/TypeScript React (FE).

---

## Current repo structure

```
ai-framework/
├── AGENTS.md                    ← global rules (13 rules, XML-tagged) — every tool reads this
├── opencode.json                ← OpenCode global config: model=sonnet-4-6, permissions
├── setup.py                     ← run once per machine, no flags needed
├── workflow-guide.md            ← day-to-day developer guide
│
├── agents/                      ← 16 agent definitions with per-agent model assignment
├── skills/                      ← 39 skill folders (all have ## Quick reference sections)
├── commands/                    ← slash commands: /task /review /first-run /handoff
├── hooks/                       ← git hooks + session-end.js (auto session summary)
│
├── instructions/
│   ├── AGENTS-reference.md      ← agent roles, task flow, skill routing (on-demand)
│   ├── CLAUDE.md                ← Claude Code additions
│   ├── COPILOT.md               ← GitHub Copilot (VS Code + IntelliJ)
│   ├── GEMINI.md                ← Gemini CLI wrapper (@imports AGENTS.md)
│   ├── VSCODE.md                ← VS Code Copilot additions
│   ├── GIT_COMMIT.md            ← commit message guidelines
│   └── codex-AGENTS.md          ← Codex CLI wrapper (adds skills block)
│
└── docs/
    ├── session-summary.md       ← this file
    └── refactoring-plan.md
```

**Deleted / renamed from earlier sessions (do not reference these):**
- `SHARED.md` → now `AGENTS.md` at root
- `SHARED-reference.md` → now `instructions/AGENTS-reference.md`
- `.opencode/` directory → contents moved to root `agents/`, `skills/`, `commands/`, `hooks/`
- `_opencode.json` → deleted (merged into `opencode.json`)
- `instructions/CURSOR.md` → deleted (Cursor support removed)
- `instructions/WINDSURF.md` → deleted (Windsurf support removed)
- `instructions/wrappers/` → deleted (wrappers now directly in `instructions/`)
- `install.sh` → deleted (replaced by `setup.py`)
- `verification/scripts/` → deleted (git hooks moved to `hooks/`)
- `bin/` → deleted (RTK downloaded at runtime by setup.py)
- `code-standards/references/solid.md` → deleted (superseded by `clean-code-solid` skill)

---

## Supported tools and how they are wired

| Tool | Global config location | Wired by |
|---|---|---|
| **OpenCode** (primary) | `~/.config/opencode/` | `setup.py` — opencode.json, AGENTS.md, agents/, skills/, commands/, hooks/ |
| **Claude Code** | `~/.claude/` | `setup.py` — CLAUDE.md, AGENTS.md, agents/, skills/, commands/, hooks/ |
| **GitHub Copilot (VS Code)** | `~/.../Code/User/settings.json` | `setup.py` — injects codeGeneration.instructions globally |
| **GitHub Copilot (IntelliJ)** | `%LOCALAPPDATA%/github-copilot/` | `setup.py` — Windows only |
| **Gemini CLI** | `~/.gemini/` | `setup.py` — GEMINI.md + skills/ symlink |
| **Codex CLI** | `~/.codex/` | `setup.py` — codex-AGENTS.md wrapper |

**Removed tools:** Cursor, Windsurf (support dropped — too much maintenance for low adoption).

---

## Agent model tiers

| Tier | Model | Agents |
|---|---|---|
| HIGH | `anthropic/claude-opus-4-8` | architect, plan-reviewer, refactor-planner |
| MID | `anthropic/claude-sonnet-4-6` | orchestrator, product-manager, backend, frontend, ui, db, api, code-reviewer, frontend-error-fixer |
| LOW | `anthropic/claude-haiku-4-5` | qa, gatekeeper, web-research-specialist |

Global default (opencode.json): `anthropic/claude-sonnet-4-6`

---

## Key rules to remember

**AGENTS.md has 14 rules + 4 checks** (XML-tagged):

**Checks:** first-run (1), branch-guard (2), investigate-before-answering (3), commit-push-pr-guard (4)

**Git operations:**
- Freely allowed: status, log, diff, branch, checkout -b (after Check 2)
- Guarded (require Check 4 approval): git add, git commit, git push, gh pr create
- Permanently forbidden: merge, rebase, reset, push --force


- Rules 1-2: git permissions + branch-before-write
- Rule 3: no 3rd-party without approval
- Rule 4: first-run mandatory when [XXX] in project-overview
- Rule 5: show before writing
- Rule 6: Clean Code + SOLID + KISS + YAGNI
- Rule 7: atomic changes (one PR = one concern)
- Rule 8: skill loading via skill-rules.json
- Rule 9: post-implementation pipeline (code-reviewer [lint+scan+review] → qa → gatekeeper)
- Rule 10: surgical changes (no over-engineering)
- Rule 11: no MCP
- Rule 12: isolated environment
- Rule 13: no routine narration

**Branch flow:** agent proposes name → developer confirms → agent runs `git checkout -b`.

**BLOCKING vs NON-BLOCKING:** SOLID violations, security issues, swallowed exceptions, missing units in numeric names = always BLOCKING.

**Context budget:** > 8 agent responses OR > ~3k token response → load `handoff`.

**Skill loading:** orchestrator reads `skills/skill-routing/skill-rules.json` at task start.

**project-overview sub-files:**
- `sub/stack.md` — every agent, every task
- `sub/patterns.md` — implementation agents + reviewers
- `sub/topology.md` — orchestrator + architect only
- `sub/tooling.md` — code-reviewer + first-run only
- `sub/localization.md` — only when UI text is involved

---

## Token reduction stack

| Tool | Layer | Status |
|---|---|---|
| RTK | Shell output filtering | Auto-installed by setup.py |
| Token Optimizer | Structural audit + compaction survival | Auto-installed by setup.py (git clone) |
| ccusage | Cross-tool token/cost monitoring | Auto-installed by setup.py (npm, or zero-install via npx) |
| opencode-usage | OpenCode per-agent policy data | Auto-installed by setup.py (uv/pip) |
| session-end.js hook | Auto session-summary at session end | Wired via ~/.claude/hooks/ |

Plus framework-level optimisations already built in:
- All skills have `## Quick reference` sections (load summary, not full content)
- All agents load `project-overview/sub/[specific-file]` not the full entrypoint
- AGENTS.md is rules-only (~130 lines); agent roles in AGENTS-reference.md (on-demand)
- Context ordering enforced: rules → skills → agent def → project-overview → task
