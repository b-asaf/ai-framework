# ai-framework

An agentic development framework that makes AI coding tools behave like a senior developer —
safe git practices, clean code enforcement, agile vertical PRs, and no risky actions without
your explicit approval.

---

## How it works

```
Install once on your machine
        ↓
Open any project folder or workspace in OpenCode
        ↓
Framework is active — no per-project setup needed
```

For VS Code / IntelliJ Copilot, run one additional command inside each project repo.

---

## Primary tool — OpenCode

OpenCode is the recommended way to use this framework. It reads global configuration
from `~/.config/opencode/` — meaning the framework is active in **every folder and
workspace** you open, automatically, after a single install.

OpenCode works with multiple AI providers: Anthropic (Claude), OpenAI, Google Gemini,
and others. You choose the model; the framework runs on top of it.

Download OpenCode: https://opencode.ai

---

## Secondary tool — GitHub Copilot

GitHub Copilot (VS Code or IntelliJ/WebStorm) is also supported. It requires one
extra command per project repo to wire the instructions file. Global wiring works
for IntelliJ on Windows.

---

## Prerequisites

Before running setup, make sure you have:

**1. Python 3.8+**

```bash
python --version    # should show Python 3.x.x
```

Download if needed: https://python.org/downloads

**2. Git**

```bash
git --version
```

Download if needed: https://git-scm.com/downloads

**3. OpenCode** (primary tool)

Download and install from https://opencode.ai, then sign in with your AI provider.

**4. GitHub Copilot** (optional, secondary tool)

Enable at https://github.com/settings/copilot, then install the extension in
VS Code (`Ctrl+Shift+X` → search "GitHub Copilot") or your JetBrains IDE
(`File → Settings → Plugins` → search "GitHub Copilot").

---

## Setup — Step 1: Install once on this machine

Clone the framework repo to a permanent location on your machine:

```bash
# Mac / Linux
git clone https://github.com/b-asaf/ai-framework.git ~/ai-framework

# Windows (run CMD as administrator)
git clone https://github.com/b-asaf/ai-framework.git "%USERPROFILE%\ai-framework"
```

Then run the global setup from inside the framework folder:

```bash
# Mac / Linux
cd ~/ai-framework
python setup.py --global

# Windows
cd "%USERPROFILE%\ai-framework"
python setup.py --global
```

This wires the framework into all AI tools detected on your machine.
You will see output like:

```
ai-framework setup
========================================
repo:    /home/you/ai-framework
mode:    symlink
step:    --global  (install once on this machine)

Detected tools:
     OpenCode          [PRIMARY]          ✔ found
     Claude Code                          – not found
     Codex CLI                            – not found
     Gemini CLI                           – not found
     Copilot IntelliJ  (Windows)          – not found
     Copilot VS Code                      ✔ found
     RTK                                  – not found

Wiring globally...
  ✔  ~/.config/opencode/opencode.json
  ✔  ~/.config/opencode/AGENTS.md
  ✔  ~/.config/opencode/agents
  ✔  ~/.config/opencode/skills

✅ Global setup complete.
```

After this, open any project folder in OpenCode — the framework is already active.

---

## Setup — Step 2: Initialize each project repo

Run this command once inside each git repository you want to work on:

```bash
# Mac / Linux — from inside your project repo
cd ~/your-project
python ~/ai-framework/setup.py --project

# Windows
cd "%USERPROFILE%\your-project"
python "%USERPROFILE%\ai-framework\setup.py" --project
```

This wires VS Code Copilot into the project and installs git hooks.
For OpenCode, this step is optional — it already works globally.

You will see:

```
Wiring into project: your-project
  ✔  your-project/.github/copilot-instructions.md
Installing git hooks...
  ✔  Git hooks installed

✅ Project setup complete.
```

After this, open the project in VS Code — Copilot is now active with the framework.

---

## Keeping the framework up to date

```bash
# Mac / Linux
cd ~/ai-framework
git pull

# Windows
cd "%USERPROFILE%\ai-framework"
git pull
```

Symlinks update automatically — no need to re-run setup after pulling.

---

## Is it working? — 5 checks

Run these after setup to confirm the framework is active.

---

**Check 1 — Wiring**

```bash
python setup.py --global --check
```

✅ Pass: all installed tools show `would link` with valid source paths.
❌ Fail: `SKIP — source not found` — run `git pull` in the framework folder
and re-run `python setup.py --global`.

---

**Check 2 — Instructions visible to the tool**

Open OpenCode (or VS Code Copilot Chat) and ask:

> "Read your instructions and tell me what Check 1 and Check 2 are."

✅ Pass: it describes the first-run project scan and the branch guard.
❌ Fail: it says it has no instructions — re-run `python setup.py --global`
and restart the tool.

---

**Check 3 — First-run analysis fires**

Open a new project in OpenCode (one that has never used this framework) and say:

> "Start a new task."

✅ Pass: the tool asks to run a first-time project scan before doing anything.
❌ Fail: it skips straight to the task — skills are not wired.
Run `python setup.py --global --check` to verify skills symlink exists.

---

**Check 4 — Branch guard fires**

Ask your tool:

> "Add a new endpoint to the API."

✅ Pass: it proposes a branch name and waits for your confirmation before
writing any file.
❌ Fail: it starts writing files — re-run Check 2 to diagnose.

---

**Check 5 — Skills loading**

Ask your tool:

> "Which skills did you load for this task and why?"

✅ Pass: it lists specific skills matched to the task type
(e.g. `pattern-enforcement`, `code-standards`, `tdd`).
❌ Fail: it says it has no skills — verify `~/.config/opencode/skills/` exists.

---

## Working with single repos and workspaces

### Single repo

```bash
cd ~/my-backend          # or any single repo
opencode                 # framework active immediately
```

### Workspace (multiple repos open together)

OpenCode supports opening a workspace (a folder containing multiple repos):

```bash
cd ~/projects            # parent folder containing be/, fe/, etc.
opencode                 # framework active for all child repos
```

Each child repo gets its own `project-overview` populated on first run.
The `repo-topology` skill detects whether this is a monorepo, multi-repo,
or hybrid and adjusts the agent routing accordingly.

### VS Code multi-root workspace

Create a `.code-workspace` file and run `setup.py --project` inside each repo:

```
workspace/
  be/           ← run: python ~/ai-framework/setup.py --project
  fe/           ← run: python ~/ai-framework/setup.py --project
  my-project.code-workspace
```

---

## Optional: RTK token reduction

RTK intercepts tool output and filters it before the AI sees it — up to 90% fewer
tokens from command output. No MCP, no external calls, no workflow change.

**Install RTK:**

```bash
# Mac / Linux
curl -fsSL https://raw.githubusercontent.com/rtk-ai/rtk/master/install.sh | sh

# Mac (Homebrew)
brew install rtk-ai/tap/rtk

# Windows — download from https://github.com/rtk-ai/rtk/releases
# Extract rtk.exe and place it in a folder on your PATH
```

**Wire RTK:**

```bash
python setup.py --global --rtk
```

---

## Other supported tools

Additional tools are wired automatically if detected during `--global` setup:

| Tool        | Install                                                   |
| ----------- | --------------------------------------------------------- |
| Claude Code | https://claude.ai/download (requires paid subscription)   |
| Gemini CLI  | `npm install -g @google/gemini-cli` (free tier available) |
| Codex CLI   | https://chatgpt.com/codex (requires ChatGPT Plus/Pro)     |

After installing any of these, re-run `python setup.py --global` and they
will be detected and wired automatically.

---

## Troubleshooting

| Problem                                  | Fix                                                              |
| ---------------------------------------- | ---------------------------------------------------------------- |
| `python: command not found`              | Try `python3 setup.py --global` instead                          |
| `Permission denied` on symlink (Windows) | Enable Developer Mode in Windows Settings, or add `--copy`       |
| Tool shows "not found" but is installed  | Restart your terminal (PATH needs to refresh), then re-run setup |
| VS Code Copilot has no instructions      | Run `python setup.py --project` from inside the project folder   |
| Skills not loading in OpenCode           | Verify `~/.config/opencode/skills/` exists — re-run `--global`   |
| OpenCode not reading global config       | Verify `~/.config/opencode/AGENTS.md` exists — re-run `--global` |
| `No .git directory` error on --project   | Run `--project` from the root of a git repo, not a parent folder |

---

## Repo structure

```
opencode.json         ← global OpenCode config (wired to ~/.config/opencode/)

instructions/
  SHARED.md           ← behavior rules — loaded globally by all tools
  SHARED-reference.md ← agent roles, task flow — loaded on-demand
  COPILOT.md          ← GitHub Copilot instructions
  CLAUDE.md           ← Claude Code additions
  GEMINI.md           ← Gemini CLI wrapper
  GIT_COMMIT.md       ← commit message guidelines
  wrappers/
    opencode-AGENTS.md  ← OpenCode global AGENTS.md
    codex-AGENTS.md     ← Codex CLI wrapper

.opencode/
  agents/             ← 16 AI agent definitions (global via ~/.config/opencode/agents/)
  skills/             ← 36 skill folders (global via ~/.config/opencode/skills/)
  verification/
    scripts/          ← git hooks (installed per-project by --project)

docs/
  session-summary.md  ← load at start of a new session to restore context

setup.py              ← setup script (--global once, --project per repo)
workflow-guide.md     ← day-to-day usage guide
```
