# ai-framework

An agentic development framework that makes AI coding tools behave like a senior
developer — safe git practices, clean code enforcement, agile vertical PRs, and
no risky actions without your explicit approval.

Install once. Open any project folder. Framework is active.

---

## Supported tools

| Tool | How it's wired |
|---|---|
| **OpenCode** ← primary | `~/.config/opencode/` — global, works in every folder |
| **Claude Code** | `~/.claude/` — global, works in every folder |
| **GitHub Copilot (VS Code)** | `~/.../Code/User/settings.json` — global settings |
| **GitHub Copilot (IntelliJ/WebStorm)** | `%LOCALAPPDATA%/github-copilot/` — global (Windows) |
| **Gemini CLI** | `~/.gemini/` — global |
| **Codex CLI** | `~/.codex/` — global |

---

## Install

### Prerequisites

**Python 3.8+**
```bash
python --version    # must show 3.x.x
```
Download if needed: https://python.org/downloads

**Git**
```bash
git --version
```
Download if needed: https://git-scm.com/downloads

**At least one AI tool** — see options below.

---

### Step 1 — Clone the framework

```bash
# Mac / Linux
git clone https://github.com/b-asaf/ai-framework.git ~/ai-framework

# Windows (run CMD as administrator)
git clone https://github.com/b-asaf/ai-framework.git "%USERPROFILE%\ai-framework"
```

### Step 2 — Run setup

```bash
# Mac / Linux
cd ~/ai-framework
python setup.py

# Windows (run CMD as administrator)
cd "%USERPROFILE%\ai-framework"
python setup.py
```

That's it. The script detects which tools are installed and wires everything
automatically — symlinks, VS Code settings, git hooks, and RTK.

**Expected output:**
```
ai-framework setup
============================================
repo: /home/you/ai-framework

Detected tools:
     OpenCode          [PRIMARY]          found
     Claude Code                          not found
     Copilot VS Code                      found
     RTK                                  not found

Wiring symlinks...
  OK   ~/.config/opencode/opencode.json
  OK   ~/.config/opencode/AGENTS.md
  OK   ~/.config/opencode/agents
  OK   ~/.config/opencode/skills
  OK   ~/.config/opencode/commands
  OK   ~/.config/opencode/hooks

Wiring VS Code Copilot...
  OK   ~/.../Code/User/settings.json

Configuring git hooks...
  OK   git init.templateDir -> /home/you/ai-framework/hooks

Setting up RTK...
  OK   RTK installed: rtk 1.x.x

Done — 6 links wired, 0 skipped.

Open any project folder in OpenCode or VS Code — framework is active.
```

### Step 3 — Open any project

```bash
cd ~/your-project
opencode          # or open VS Code in this folder
```

The framework activates automatically. No project-level setup needed.

---

## Install AI tools

Install whichever tools you want. Re-run `python setup.py` after installing
any new tool — it will detect and wire it automatically.

### OpenCode (recommended — works with any AI provider)
```bash
curl -fsSL https://opencode.ai/install | bash
```
https://opencode.ai

### GitHub Copilot
Enable at https://github.com/settings/copilot, then install the extension:
- **VS Code:** `Ctrl+Shift+X` → search "GitHub Copilot" → Install
- **IntelliJ/WebStorm:** `File → Settings → Plugins` → search "GitHub Copilot" → Install

### Claude Code
```bash
# Mac / Linux
curl -fsSL https://claude.ai/install.sh | sh

# Windows (PowerShell as admin)
irm https://claude.ai/install.ps1 | iex
```
Requires a paid Claude subscription (Pro $20/mo or higher).

### Gemini CLI
```bash
npm install -g @google/gemini-cli    # requires Node.js 18+
```
Free tier available. https://nodejs.org for Node.js.

### Codex CLI (OpenAI)
```bash
# Mac / Linux
curl -fsSL https://chatgpt.com/codex/install.sh | sh

# Windows (PowerShell as admin)
powershell -ExecutionPolicy ByPass -c "irm https://chatgpt.com/codex/install.ps1 | iex"
```
Requires ChatGPT Plus/Pro or an OpenAI API key.

---

## Keep up to date

```bash
cd ~/ai-framework    # or %USERPROFILE%\ai-framework on Windows
git pull
```

Symlinks update automatically — no need to re-run setup after pulling.

---

## Is it working? — 5 checks

Run these after setup to confirm the framework is active.

**Check 1 — Wiring looks correct**

Re-run setup to verify:
```bash
python setup.py
```
All installed tools should show `OK` lines. No `FAIL` lines.

**Check 2 — Tool reads the instructions**

Open OpenCode (or Copilot Chat in VS Code) in any project folder and ask:
> "Read your instructions and tell me what Check 1 and Check 2 are."

✅ Pass: it describes the first-run project scan and the branch guard.
❌ Fail: it says it has no instructions — re-run `python setup.py` and restart the tool.

**Check 3 — First-run fires on a new project**

Open a project that has never used this framework and say:
> "Start a new task."

✅ Pass: the tool asks to run a first-time project scan before doing anything.
❌ Fail: it skips straight to the task — skills are not wired correctly.

**Check 4 — Branch guard fires**

Ask your tool:
> "Add a new endpoint to the API."

✅ Pass: it proposes a branch name and waits for your confirmation.
❌ Fail: it starts writing files without asking.

**Check 5 — Skills loading**

Ask your tool:
> "Which skills did you load for this task and why?"

✅ Pass: it lists specific skills (`pattern-enforcement`, `code-standards`, `tdd`, etc.).
❌ Fail: it says it has no skills — verify the skills symlink exists.

---

## Repo structure

```
AGENTS.md                   ← behavior rules — read by every tool, every session
opencode.json               ← OpenCode global config (model, permissions)

agents/                     ← 16 AI agent role definitions
skills/                     ← 36 skill folders
commands/                   ← slash commands (/task, /review, /first-run, /handoff)
hooks/                      ← git hooks (pre-commit, pre-push, commit-msg)

instructions/
  AGENTS-reference.md       ← agent roles, task flow — loaded on-demand
  CLAUDE.md                 ← Claude Code additions
  COPILOT.md                ← GitHub Copilot instructions
  GEMINI.md                 ← Gemini CLI wrapper
  VSCODE.md                 ← VS Code Copilot additions
  GIT_COMMIT.md             ← commit message guidelines
  codex-AGENTS.md           ← Codex CLI wrapper (adds skills block)

docs/
  session-summary.md        ← load at start of a new session to restore context
  refactoring-plan.md

setup.py                    ← run once per machine
workflow-guide.md           ← day-to-day usage guide
```

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `python: command not found` | Try `python3 setup.py` instead |
| `Permission denied` on symlink (Windows) | Run CMD as administrator, or enable Developer Mode in Windows Settings |
| Tool shows "not found" but is installed | Restart your terminal (PATH needs to refresh), then re-run setup |
| VS Code Copilot has no instructions | Re-run `python setup.py` — it updates `settings.json` automatically |
| Skills not loading | Verify `~/.config/opencode/skills` or `~/.claude/skills` exists |
| RTK download failed | Install manually: https://github.com/rtk-ai/rtk/releases |
| Git hooks not firing | Run `git init` in your existing repo to apply the template |
