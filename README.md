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

## How tool selection works

`setup.py` never asks you to choose a tool. It detects what's installed on your
machine and wires all of them simultaneously. Opening a project in OpenCode,
VS Code, or any other supported tool automatically picks up the framework.

**Detection — two signals per tool (either one is enough):**

| Tool | Detected when |
|---|---|
| OpenCode | `opencode` on PATH **or** `~/.config/opencode/` exists |
| Claude Code | `claude` on PATH **or** `~/.claude/` exists |
| Copilot VS Code | `code` on PATH **or** VS Code `settings.json` exists |
| Copilot IntelliJ | `%LOCALAPPDATA%/github-copilot/intellij/` exists (Windows only) |
| Gemini CLI | `gemini` on PATH **or** `~/.gemini/` exists |
| Codex CLI | `codex` on PATH **or** `~/.codex/` exists |

**What gets wired per tool:**

- **OpenCode** — `opencode.json` (model + permissions), `AGENTS.md`, `agents/`,
  `skills/`, `commands/`, `hooks/` → `~/.config/opencode/`. Most complete wiring.
- **Claude Code** — `CLAUDE.md`, `AGENTS.md`, `agents/`, `skills/`, `commands/`,
  `hooks/` → `~/.claude/`. Full feature parity with OpenCode.
- **VS Code Copilot** — writes instruction file paths directly into VS Code's global
  `settings.json` (`codeGeneration.instructions` + `commitMessageGeneration.instructions`).
  No per-project step needed — active in every VS Code window immediately.
- **IntelliJ/WebStorm Copilot** — `COPILOT.md`, `AGENTS.md`, `GIT_COMMIT.md`
  symlinked into the Copilot global config folder. Windows only.
- **Gemini CLI** — `GEMINI.md` (which `@imports AGENTS.md`) + `skills/` →
  `~/.gemini/`. Gemini's native skill discovery picks them up automatically.
- **Codex CLI** — `codex-AGENTS.md` (which `@imports AGENTS.md` + `skills:` block)
  → `~/.codex/`.

**Which tool runs on a given session:**

Whichever tool you open — the framework is passive. Run `opencode` from a project
folder and OpenCode reads its config. Open VS Code and Copilot reads its instructions.
You switch tools; the framework follows.

**OpenCode as primary — why:**

OpenCode is the only tool that natively supports per-agent model overrides
(so `architect` uses Opus while `linter` uses Haiku), global skill discovery,
slash commands (`/task`, `/review`), and lifecycle hooks. Claude Code supports
most of these too. VS Code Copilot and IntelliJ support instructions only —
no per-agent models, no slash commands, no hooks. For the full framework
capability, use OpenCode or Claude Code.



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
automatically — symlinks, VS Code settings, git hooks, and token-reduction tools
(RTK, Headroom, Token Optimizer).

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

Setting up Headroom...
  OK   Headroom installed: headroom 1.x.x

Setting up Token Optimizer...
  OK   token-optimizer/claude installed

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

## Token usage reduction

`setup.py` auto-installs three complementary tools that each cut waste at a
different layer. They don't overlap — running all three together is the
intended setup, not redundant.

| Tool | Layer | What it does |
|---|---|---|
| **RTK** | Shell output | Filters verbose command output (test runs, builds, git logs) before the LLM reads it |
| **Headroom** | Context compression | Compresses files, conversation history, and tool output entering the context window |
| **Token Optimizer** | Structural + behavioral audit | Finds bloated configs, unused skills, stale memory, model misrouting; checkpoints session state so compression survives auto-compaction |

All three install automatically during `python setup.py` if their prerequisites
(git, pip) are available. If a tool fails to install, setup continues — none
of them are required for the framework to work.

**Token Optimizer note:** licensed under PolyForm Noncommercial 1.0.0 — free
for personal, research, and educational use. Commercial use requires a
separate license from the author. After install, run the one-time audit
yourself inside Claude Code with `/token-optimizer` — it presents diffs for
approval before changing anything, it does not run automatically.

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

## Versioning and branches

The framework uses two branches:

- `main` — stable, tested across at least one real project
- `develop` — active work, may be unstable

Changes are documented in `CHANGELOG.md`.

To follow stable releases only:
```bash
git checkout main
git pull
```

To get the latest changes (may be unstable):
```bash
git checkout develop
git pull
```

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
AGENTS.md                   ← behavior rules (13 rules, XML-tagged) — every tool reads this
opencode.json               ← OpenCode global config (model: sonnet-4-6, permissions)

agents/                     ← 16 agent definitions (each has model: field for cost tiering)
skills/                     ← 39 skill folders (each has ## Quick reference section)
commands/                   ← slash commands (/task, /review, /first-run, /handoff)
hooks/                      ← git hooks + session-end.js (auto session summary)

instructions/
  AGENTS-reference.md       ← agent roles, task flow, skill routing — loaded on-demand
  CLAUDE.md                 ← Claude Code additions
  COPILOT.md                ← GitHub Copilot (VS Code + IntelliJ)
  GEMINI.md                 ← Gemini CLI wrapper (@imports AGENTS.md)
  VSCODE.md                 ← VS Code Copilot additions
  GIT_COMMIT.md             ← commit message guidelines
  codex-AGENTS.md           ← Codex CLI wrapper (@imports AGENTS.md + skills block)

docs/
  session-summary.md        ← current framework state — load at start of new session
  refactoring-plan.md       ← auto-generated by first-run analysis if issues found

setup.py                    ← run once per machine
workflow-guide.md           ← day-to-day developer guide
```

**Agent model tiers:**

| Tier | Model | Agents |
|---|---|---|
| HIGH | `anthropic/claude-opus-4-8` | architect, plan-reviewer, refactor-planner |
| MID | `anthropic/claude-sonnet-4-6` | orchestrator, product-manager, backend, frontend, ui, db, api, code-reviewer, frontend-error-fixer |
| LOW | `anthropic/claude-haiku-4-5` | linter, qa, gatekeeper, web-research-specialist |

---

## Agent and skill trigger reference

Understanding what fires automatically vs what you control is important for working
with the framework efficiently. Everything listed as automatic happens without any
action from you — just open a project and start a task.

### Agents

| Agent | Trigger | When |
|---|---|---|
| `orchestrator` | **Automatic** | Entry point — fires on every task |
| `product-manager` | **Automatic** | Orchestrator routes here on every task start |
| `architect` | **Automatic** | After spec is confirmed by developer |
| `plan-reviewer` | **Automatic** | After every HLD — before any implementation |
| `backend` / `frontend` / `ui` / `db` / `api` | **Automatic** | Orchestrator routes based on task scope |
| `linter` | **Automatic** | After every implementation step |
| `code-reviewer` | **Automatic** | After linter passes |
| `qa` | **Automatic** | After code review passes |
| `gatekeeper` | **Automatic** | Final gate before every handoff |
| `frontend-error-fixer` | **Automatic** (conditional) | Only when a frontend error is present |
| `refactor-planner` | **You trigger** | When you explicitly decide to plan a refactor |
| `web-research-specialist` | **You trigger** | Rule 12 (isolated environment) — ask the orchestrator "search the web for X?" and confirm |

### Skills — always-load (fire on every task)

| Skill | Who loads it |
|---|---|
| `agent-guidelines` | Every agent |
| `surgical-changes` | Every implementation agent |
| `project-overview/sub/stack.md` | Every agent |
| `code-standards` | Implementation agents + code-reviewer |
| `static-code-analysis` | Linter + code-reviewer (as precheck) |

### Skills — automatic conditional (fire when conditions are met)

| Skill | Condition |
|---|---|
| `first-run-analysis` | `project-overview` is empty or contains `[XXX]` |
| `zoom-out` | First session on a project (after first-run) or long gap between sessions |
| `repo-topology` | During first-run analysis or any cross-service task |
| `diagnose` | Task type is a bug fix |
| `tdd` | Writing code for a feature or fix |
| `grill-me` | Requirements or design are ambiguous |
| `pattern-enforcement` | Writing any file in a new domain or module |
| `third-party-policy` | Any dependency is being added, removed, or updated |
| `atomic-changes` | Any task involving a PR breakdown |
| `branching-policy` | Any task that writes files |
| `localization` | Task involves UI text, strings, or CSS layout |
| `api-contracts` | API contract or 3rd party integration work |
| `db-patterns` | Database work detected |
| `domain-model` | Unfamiliar domain terminology encountered |
| `documentation` | After changes that affect architecture or API |
| `git-hooks` | During first-run analysis |
| `clean-code-*` skills | Based on file types in the diff (code-reviewer loads selectively) |
| `clean-code-security` | Any code touching auth, input, persistence, or external APIs |
| `platform-guard` | Capacitor project + React-vs-native decision needed |
| `capacitor-bridge` | Capacitor plugin or platform-specific code in diff |
| `readability-cognitive-load` | Any implementation or review task |
| `linting-tools` | Linter agent always loads it |
| `testing-strategy` | QA agent always loads it |
| `xray-scanning` | Linter agent always loads it |

### Skills — auto-triggered by context budget (Rule 14)

These fire automatically when session length exceeds thresholds —
no action needed from you:

| Skill | Threshold |
|---|---|
| `caveman` | > 8 orchestrator responses OR any response > ~3,000 tokens |
| `handoff` | Same — fires together with `caveman` |

### Skills — you trigger (human-invoked)

These only fire when you explicitly ask for them.
Use them as slash commands (`/` prefix in OpenCode/Claude Code)
or by telling the orchestrator directly:

| Skill / Command | How to invoke | What it does |
|---|---|---|
| `excalidraw-sequence-diagram` | "Draw a sequence diagram for X" | Creates Excalidraw JSON for service flows |
| `improve-codebase-architecture` | "Review the architecture" or `/arch-review` | Finds shallow-to-deep module opportunities |
| `refactor-planner` (agent) | "Plan a refactor of X" | Safe incremental refactor plan before any code changes |
| `web-research-specialist` (agent) | "Search the web for X" | External research — requires your explicit confirmation (Rule 12) |
| `caveman` | "Be brief" / "caveman mode" | Compressed output — also fires automatically at budget threshold |
| `handoff` | "Handoff" / `/handoff` | Session compact — also fires automatically at budget threshold |
| `zoom-out` | "Zoom out" / "orient me" | Orientation map — also fires automatically on first session |
| `first-run-analysis` | "Re-scan the project" | Manual refresh of project-overview (auto-fires on `[XXX]`) |
| `repo-topology` | "Detect the topology" | Manual topology re-detection (auto-fires during first-run) |

---



| Problem | Fix |
|---|---|
| `python: command not found` | Try `python3 setup.py` instead |
| `WinError 1314` on file symlinks (Windows) | Enable Developer Mode: `Settings → System → For developers → Developer Mode → ON` then re-run. Or just re-run — setup now auto-falls back to file copies when symlinks aren't available |
| `Permission denied` on symlink (Windows) | Same as above — enable Developer Mode |
| After `git pull` files seem stale (Windows copy mode) | Re-run `python setup.py` — copies don't auto-update like symlinks. Permanently fix by enabling Developer Mode |
| Tool shows "not found" but is installed | Restart your terminal (PATH needs to refresh), then re-run setup |
| VS Code Copilot has no instructions | Re-run `python setup.py` — it updates `settings.json` automatically |
| Skills not loading | Verify `~/.config/opencode/skills` or `~/.claude/skills` exists |
| RTK download failed | Install manually: https://github.com/rtk-ai/rtk/releases |
| Headroom install failed | Install manually: `pip install headroom-ai` |
| Token Optimizer not installing | Each tool has its own install path — see "Token usage reduction" section above |
| Git hooks not firing | Run `git init` in your existing repo to apply the template |
