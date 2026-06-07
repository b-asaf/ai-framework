# ai-framework

Agentic development framework for teams using AI coding tools.
Single source of truth for instructions, skills, agents, and workflow rules —
Works across all major LLM tools with zero drift.

---

## Supported tools

| Tool | Instructions file wired |
|---|---|
| **Claude Code** | `~/.claude/CLAUDE.md` + skills + agents |
| **OpenCode** | `~/.config/opencode/AGENTS.md` |
| **Codex CLI** | `~/.codex/AGENTS.md` |
| **Copilot IntelliJ** | `global-copilot-instructions.md` + agents + git commit |

All tools read from `instructions/SHARED.md` as the single source of truth.
Tool-specific files (`CLAUDE.md`, `COPILOT.md`) layer additions on top.

---

## Prerequisites

- Python 3.8+ (stdlib only, no pip install needed)
- **Windows only:** Enable Developer Mode for symlinks without admin rights
  (`Settings → System → Developer Mode → On`), or run with `--copy`

---

## Setup (new machine)

**1. Clone the repo**

```bash
# Mac / Linux
git clone https://github.com/b-asaf/ai-framework.git ~/ai-framework

# Windows (PowerShell)
git clone https://github.com/b-asaf/ai-framework.git "$env:USERPROFILE\ai-framework"
```

**2. Run setup**

```bash
python setup.py
```

That's it. The script creates symlinks from each tool's config location into
this repo. Re-run any time to repair broken links after re-cloning.

**Options**

```
python setup.py            # symlink everything (default, recommended)
python setup.py --copy     # copy instead of symlink (CI / restricted envs)
python setup.py --check    # dry-run: show what would happen without changing anything
python setup.py --help
```

**3. Keep up to date**

```bash
git pull
```

No re-run needed. Tools read through the symlinks, so a pull is instantly live.
If you used `--copy`, re-run `setup.py` after pulling.

---

## Repo structure

```
instructions/
  SHARED.md        ← single source of truth — all tools derive from this
  CLAUDE.md        ← Claude Code-specific additions
  COPILOT.md       ← Copilot IntelliJ-specific additions
  GIT_COMMIT.md    ← commit message guidelines

skills/            ← reusable skill definitions (loaded on-demand)
agents/            ← sub-agent role definitions
docs/              ← specs, refactoring plans, ADRs

_opencode.json     ← OpenCode workspace config (model, permissions, instructions)
workflow-guide.md  ← day-to-day developer guide
```

---

## What gets wired up

```
instructions/SHARED.md  ──→  ~/.config/opencode/AGENTS.md
                         ──→  ~/.codex/AGENTS.md
                         ──→  %LOCALAPPDATA%/github-copilot/.../global-agents-instructions.md

instructions/CLAUDE.md  ──→  ~/.claude/CLAUDE.md

instructions/COPILOT.md ──→  %LOCALAPPDATA%/github-copilot/.../global-copilot-instructions.md

instructions/GIT_COMMIT.md ──→  %LOCALAPPDATA%/github-copilot/.../global-git-commit-instructions.md

skills/                 ──→  ~/.claude/skills/
agents/                 ──→  ~/.claude/agents/
```

---

## Adding content

| What | Where | Note |
|---|---|---|
| Shared behavior rule | `instructions/SHARED.md` | Propagates to all tools automatically |
| Claude Code-only rule | `instructions/CLAUDE.md` | |
| Copilot-only rule | `instructions/COPILOT.md` | |
| New skill | `skills/<name>/skill.md` | Load on-demand per task |
| New agent | `agents/<name>.md` | |

---

## First-run analysis

The first time you open a project in any supported tool, the orchestrator
runs a full first-run analysis before accepting any task:

1. Detects topology (monolith vs microservices)
2. Determines repo state (new / partial / mature)
3. Detects language, framework, build tool, test framework per repo
4. Discovers existing conventions and flags violations
5. Generates `docs/refactoring-plan.md` if issues are found

You will be asked to confirm the detected stack before agents start enforcing it.

---

## Troubleshooting

| Problem | Solution |
|---|---|
| `Permission denied` on symlink | Enable Windows Developer Mode, or run `python setup.py --copy` |
| Tool not picking up instructions | Re-run `python setup.py --check` to verify links are correct |
| Copilot links skipped | Expected on Mac/Linux — Copilot wiring is Windows-only |
| Skills not found | Verify `~/.claude/skills/` exists — re-run `python setup.py` |
| Want to see what setup does before running | `python setup.py --check` |
