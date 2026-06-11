# ai-framework

Agentic development framework for teams using AI coding tools.
Single source of truth for instructions, skills, agents, and workflow rules —
works across all major LLM tools with zero drift.

**Constraints:** no MCP, isolated environment (no external network calls).

---

## Supported tools

| Tool | Instructions file wired |
|---|---|
| **Claude Code** | `~/.claude/CLAUDE.md` + skills + agents |
| **OpenCode** | `~/.config/opencode/AGENTS.md` |
| **Codex CLI** | `~/.codex/AGENTS.md` |
| **Gemini CLI** | `~/.gemini/GEMINI.md` + skills |
| **Cursor** | `~/.cursor/rules/shared.mdc` |
| **Windsurf** | `~/.codeium/windsurf/memories/global-rules.md` |
| **VS Code Copilot** | `.github/copilot-instructions.md` (project-level) |
| **Copilot IntelliJ** | `global-copilot-instructions.md` + agents + git commit (Windows) |

All tools derive from `instructions/SHARED.md` as the single source of truth.
Tool-specific files layer additions on top. Codex and OpenCode use wrapper files
that import SHARED.md, so RTK can safely append its block without breaking wiring.

---

## Prerequisites

- Python 3.8+ (stdlib only — no pip install needed)
- **Windows only:** Enable Developer Mode for symlinks (`Settings → Developer Mode → On`),
  or run with `--copy`

---

## Setup (new machine)

**1. Clone the repo**

```bash
# Mac / Linux
git clone https://azuredevops.rafael.co.il/Almagor_V2_Collection/C2Apps/_git/AI-Team ~/ai-framework

# Windows (PowerShell)
git clone https://azuredevops.rafael.co.il/Almagor_V2_Collection/C2Apps/_git/AI-Team "$env:USERPROFILE\ai-framework"
```

**2. Run setup**

```bash
python setup.py
```

The script detects which tools are installed and wires only those.
Re-run any time to repair broken links.

**Options**

```
python setup.py                  # symlink everything (default, recommended)
python setup.py --copy           # copy instead of symlink (CI / restricted envs)
python setup.py --check          # dry-run: show what would happen without changing anything
python setup.py --install-hooks  # also install git hooks into .git/hooks/
python setup.py --rtk            # also run rtk init for each detected tool
python setup.py --help
```

**3. Optional: install RTK for token reduction**

RTK intercepts shell tool calls and filters their output before the LLM sees it —
up to 90% fewer tokens from command output, no change to your workflow, no MCP.

```bash
# Install RTK first (see https://www.rtk-ai.app)
python setup.py --rtk
```

RTK is optional. The framework works fully without it.

**4. Keep up to date**

```bash
git pull
```

Symlinks update instantly. If you used `--copy`, re-run `setup.py` after pulling.

---

## Repo structure

```
instructions/
  SHARED.md             ← rules only (~120 lines) — global, loaded every session
  SHARED-reference.md   ← agent roles, task flow, routing — loaded on-demand
  CLAUDE.md             ← Claude Code additions
  GEMINI.md             ← Gemini CLI wrapper (@imports SHARED.md)
  CURSOR.md             ← Cursor additions
  WINDSURF.md           ← Windsurf additions
  VSCODE.md             ← VS Code Copilot (project-level)
  COPILOT.md            ← Copilot IntelliJ additions
  GIT_COMMIT.md         ← commit message guidelines
  wrappers/
    codex-AGENTS.md     ← Codex wrapper (@imports SHARED.md + skills block)
    opencode-AGENTS.md  ← OpenCode wrapper (@imports SHARED.md)

.opencode/
  agents/               ← 16 agent definitions
  skills/               ← 36 skill folders + skill-routing/skill-rules.json
  verification/scripts/ ← git hooks

docs/
  session-summary.md    ← load at start of new session to restore context
  refactoring-plan.md

_opencode.json          ← OpenCode workspace config (model, permissions)
setup.py                ← one-command setup for all tools
workflow-guide.md       ← day-to-day developer guide
```

---

## Key structural rules

- `SHARED.md` is **rules only** — checks, git permissions, non-negotiables. ~120 lines.
- `SHARED-reference.md` has agent roles and routing — loaded by orchestrator only, not globally.
- `project-overview/SKILL.md` is a thin entrypoint. Agents load sub-files selectively:
  - `sub/stack.md` — every agent, every task
  - `sub/patterns.md` — implementation agents + reviewers
  - `sub/topology.md` — orchestrator + architect only
  - `sub/tooling.md` — linter + first-run only
  - `sub/localization.md` — only when UI text is involved

---

## Troubleshooting

| Problem | Solution |
|---|---|
| `Permission denied` on symlink | Enable Windows Developer Mode, or `python setup.py --copy` |
| Tool not picking up instructions | `python setup.py --check` to verify links |
| Gemini skills not loading | Verify `~/.gemini/skills/` exists — re-run `python setup.py` |
| RTK not intercepting | Run `python setup.py --rtk`, then restart the tool |
| Copilot IntelliJ skipped | Expected on Mac/Linux — Windows only |
| Want to preview changes | `python setup.py --check` |
