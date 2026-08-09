# ai-framework

**Version 1.8.0** — see [`CHANGELOG.md`](CHANGELOG.md) for what changed. The
same version prints at the top of every `python setup.py` / `python setup.py
--verify` run, so your installed copy and this README never disagree about
which version you're on.

An agentic development framework that makes AI coding tools behave like a senior
developer — safe git practices, clean code enforcement, agile vertical PRs, and
no risky actions without your explicit approval.

Install once. Open any project folder. Framework is active.

---

## Supported tools

| Tool                                   | How it's wired                                        |
| -------------------------------------- | ----------------------------------------------------- |
| **OpenCode** ← primary                 | `~/.config/opencode/` — global, works in every folder |
| **Claude Code**                        | `~/.claude/` — global, works in every folder          |
| **GitHub Copilot (VS Code)**           | `~/.../Code/User/settings.json` — global settings     |
| **GitHub Copilot (IntelliJ/WebStorm)** | `%LOCALAPPDATA%/github-copilot/` — global (Windows)   |
| **Gemini CLI**                         | `~/.gemini/` — global                                 |
| **Codex CLI**                          | `~/.codex/` — global                                  |

---

## How tool selection works

`setup.py` never asks you to choose a tool. It detects what's installed on your
machine and wires all of them simultaneously. Opening a project in OpenCode,
VS Code, or any other supported tool automatically picks up the framework.

**Detection — two signals per tool (either one is enough):**

| Tool             | Detected when                                                   |
| ---------------- | --------------------------------------------------------------- |
| OpenCode         | `opencode` on PATH **or** `~/.config/opencode/` exists          |
| Claude Code      | `claude` on PATH **or** `~/.claude/` exists                     |
| Copilot VS Code  | `code` on PATH **or** VS Code `settings.json` exists            |
| Copilot IntelliJ | `%LOCALAPPDATA%/github-copilot/intellij/` exists (Windows only) |
| Gemini CLI       | `gemini` on PATH **or** `~/.gemini/` exists                     |
| Codex CLI        | `codex` on PATH **or** `~/.codex/` exists                       |

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
(so `architect` uses Opus while `gatekeeper` uses Haiku), global skill discovery,
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

# Windows
git clone https://github.com/b-asaf/ai-framework.git "%USERPROFILE%\ai-framework"
```

### Step 2 — Run setup

```bash
# Mac / Linux
cd ~/ai-framework
python setup.py

# Windows — no admin rights needed
cd "%USERPROFILE%\ai-framework"
python setup.py
```

That's it. No admin rights required. The script detects which tools are
installed and wires everything automatically — symlinks (or file copies,
if your machine can't symlink — see below), VS Code settings, git hooks,
and token-reduction tools (RTK, Token Optimizer). Anything it can't do
itself (like installing `gh`) is listed clearly at the end under
"Action required," with exact steps to fix it.

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

Setting up Token Optimizer...
  OK   token-optimizer/claude installed

Checking GitHub CLI (gh)...
  OK   gh found: gh version 2.x.x

Setup complete — 6 links wired and verified.

Open any project folder in OpenCode or VS Code — framework is active.
To update: cd ai-framework && git pull && python setup.py
To re-check tool status without changing anything: python setup.py --verify

============================================
Action required — none. Everything checked out.
```

If something needs your attention (e.g. `gh` isn't installed, or your
machine can't create file symlinks), it's collected into a single
"Action required" block at the end instead of being buried mid-log —
each item includes exactly what to run or click. Re-check status anytime
without touching any files: `python setup.py --verify`.

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

| Tool                | Layer                         | What it does                                                                                                                                                                                                                         |
| ------------------- | ----------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **RTK**             | Shell output                  | Filters verbose command output (test runs, builds, git logs) before the LLM reads it                                                                                                                                                 |
| **Token Optimizer** | Structural + behavioral audit | Finds bloated configs, unused skills, stale memory, model misrouting; checkpoints session state so compression survives auto-compaction                                                                                              |
| **Graphify**        | Codebase exploration          | Pre-builds a local, deterministic call/import graph (tree-sitter, zero LLM cost). Agents query it (`graphify explain`, `graphify path`) instead of reading files one by one to figure out structure — see `skills/graphify/SKILL.md` |

All three install automatically during `python setup.py` if their prerequisites
(git, uv/pipx) are available. If a tool fails to install, setup continues —
none is required for the framework to work.

**Token Optimizer note:** licensed under PolyForm Noncommercial 1.0.0 — free
for personal, research, and educational use. Commercial use requires a
separate license from the author. After install, run the one-time audit
yourself inside Claude Code with `/token-optimizer` — it presents diffs for
approval before changing anything, it does not run automatically.

**Graphify note:** the graph is meant to be committed (`graphify-out/`) so
the whole team starts oriented and every session skips re-deriving structure
from scratch. `python setup.py` registers Graphify assistants globally, but the
repo-specific rebuild hook should be installed inside each opened project with
`cd <project> && graphify hook install`. For repos large enough that `graph.html`
becomes unwieldy (~5000+ nodes), use `scripts/graphify-smart-viz.sh`
instead of calling `graphify` directly — it extracts with `--no-viz` first,
checks the node count, and only generates HTML under the threshold.

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

## Is it working? — 6 steps

Run these after setup to confirm the framework is active. (These are
independent verification steps for confirming your *install* — not the
same numbering as the workflow "Check 1"/"Check 2"/"Check 4" that AGENTS.md
and `commands/task.md` refer to; Step 2 below actually asks the tool to
recite those.)

**Step 1 — Wiring looks correct**

Re-run setup to verify:

```bash
python setup.py
```

All installed tools should show `OK` lines. No `FAIL` lines.

**Step 2 — Tool reads the instructions**

Open OpenCode (or Copilot Chat in VS Code) in any project folder and ask:

> "Read your instructions and tell me what Check 1 and Check 2 are."

✅ Pass: it describes the first-run project scan and the branch guard.
❌ Fail: it says it has no instructions — re-run `python setup.py` and restart the tool.

**Step 3 — First-run fires on a new project**

Open a project that has never used this framework and say:

> "Start a new task."

✅ Pass: the tool asks to run a first-time project scan before doing anything.
❌ Fail: it skips straight to the task — skills are not wired correctly.

**Step 4 — Branch guard fires**

Ask your tool:

> "Add a new endpoint to the API."

✅ Pass: it proposes a branch name and waits for your confirmation.
❌ Fail: it starts writing files without asking.

**Step 5 — Skills loading**

Ask your tool:

> "Which skills did you load for this task and why?"

✅ Pass: it lists specific skills (`pattern-enforcement`, `code-standards`, `tdd`, etc.).
❌ Fail: it says it has no skills — verify the skills symlink exists.

**Step 6 — The push gate is actually enforced, not just instructed**

This is the one step that doesn't involve the AI tool at all — it confirms `build-verify` is a real git hook, not just an instruction an agent could skip.

```bash
cat .git/hooks/pre-push   # should contain build-verify.sh logic, not just branch protection
cat .ai-framework.json    # should exist after first-run analysis, with real lint/format/test commands
```

Then try pushing a commit that deliberately fails lint (or temporarily set `"test": "exit 1"` in `.ai-framework.json`) and run `git push`.

✅ Pass: the push is blocked with `❌ build-verify failed — push blocked.`, independent of whether any agent is even running.
❌ Fail: the push succeeds — `.git/hooks/pre-push` is stale. Run `git init` in the project (safe, just refreshes hooks) or re-run `python setup.py` from the ai-framework folder first.

---

## Everything you can trigger manually

Most of the framework runs automatically (see [Agent and skill trigger
reference](#agent-and-skill-trigger-reference) below for the full automatic
list). This section is the opposite view: everything **you** have to ask for
by name, in one place, so nothing manual gets lost in the automatic tables.

**Slash commands** (type `/` in OpenCode/Claude Code, or ask in plain English):

| Command      | What it does                                                                                         |
| ------------ | ---------------------------------------------------------------------------------------------------- |
| `/task`      | Start a new task — runs Check 1/2, then product-manager → architect → plan-reviewer → implementation |
| `/review`    | Full post-implementation pipeline on the current branch — code-reviewer, qa, gatekeeper              |
| `/first-run` | Manually re-run first-run analysis (project-overview is stale or has `[XXX]`)                        |
| `/handoff`   | Compact the session — saves a handoff doc, appends to `docs/session-summary.md`                      |

**Running `/review` — no arguments, no separate setup:**

1. `git checkout` your **feature branch** (the source branch — not `main`/`develop`). The command reviews "the current branch," so it needs to be the one with your changes checked out.
2. Commit locally first, even if you haven't pushed. `code-reviewer` reads the diff via `git diff`, and an uncommitted working tree is not a reliable diff source.
3. Type `/review` — no branch names, no flags. It diffs your current branch against the repo's protected base (`main`/`master`/`develop`) automatically.
4. Same session as your implementation or a brand-new one both work — git state lives on disk, not in the conversation. For a long/noisy implementation session, a fresh session (or `/handoff` first) keeps the review's context cleaner and cheaper.
5. Read the verdict: **PASS** or **FAIL**. Findings are grouped **by file, then by line** — read it like inline PR comments rather than a flat list.

Runs entirely on your existing Claude Code/OpenCode session — no API key, no CI, no separate account.

**Want the findings as real inline GitHub PR comments**, not just in chat? `code-reviewer` stays read-only by default — ask for it explicitly after `/review` finishes (e.g. "post these as inline PR comments"). Requires an open PR and `gh` authenticated; you'll get a confirmation prompt before anything is posted.

**Reviewing someone else's pushed branch:** works the same way — pull it locally first, then run `/review` exactly as above. It doesn't matter whose branch it is; the diff is always taken against the protected base, not against your own history.

```bash
git fetch origin
git checkout -b their-branch origin/their-branch   # or: git checkout their-branch, if already tracked
/review
```

Make sure your own working tree is clean first so nothing of yours leaks into their diff.

**Agents you trigger** (say what you want — no slash command needed):

| Agent                     | Say                    | What it does                                                                                |
| ------------------------- | ---------------------- | ------------------------------------------------------------------------------------------- |
| `refactor-planner`        | "Plan a refactor of X" | Safe incremental refactor plan before any code changes                                      |
| `web-research-specialist` | "Search the web for X" | External research — Rule 12 means it never fires on its own, always needs your confirmation |

**Skills you trigger:** see the [human-invoked skills table](#skills--you-trigger-human-invoked) — `excalidraw-sequence-diagram`, `improve-codebase-architecture`, `caveman`, `handoff`, `zoom-out`, `first-run-analysis`, `repo-topology`, `graphify`.

**Standalone CLI tools** (run from your terminal, not through the agent):

| Tool                       | Run                                                                                | What it does                                                                                              |
| -------------------------- | ---------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------- |
| Token Optimizer audit      | `/token-optimizer` inside Claude Code                                              | One-time audit for bloated configs/unused skills — presents diffs for approval, doesn't run automatically |
| Graphify always-on install | `graphify <platform> install` (e.g. `graphify opencode install`), once per project | Makes the agent auto-prefer the graph over Read/Glob — not wired by `setup.py` since it's per-project     |
| Graphify rebuild hook      | `graphify hook install`, once per project                                          | Keeps `graphify-out/graph.json` current on every commit                                                   |
| Graphify large-repo viz    | `scripts/graphify-smart-viz.sh <path>`                                             | Safe graph visualization — auto-skips HTML past ~5000 nodes                                               |
| Setup health check         | `python setup.py --verify`                                                         | Read-only — prints what still needs attention without changing anything                                   |

---

## Repo structure

```
AGENTS.md                   ← behavior rules (14 rules, XML-tagged) — every tool reads this
opencode.json               ← OpenCode global config (model: sonnet-4-6, permissions)

agents/                     ← 15 agent definitions (each has model: field for cost tiering)
skills/                     ← 42 skill folders (most have a ## Quick reference section)
commands/                   ← slash commands (/task, /review, /first-run, /handoff)
hooks/                      ← two unrelated kinds, same folder: git hooks (pre-commit, commit-msg, pre-push, build-verify.sh, install-hooks.sh — wired via git init.templateDir, fire on git events) + session-end.js (Claude Code's own Stop-event hook, wired via ~/.claude/hooks/, fires on session end)
scripts/                    ← graphify-smart-viz.sh (node-count-aware graph visualization)

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

| Tier | Model                         | Agents                                                                                             |
| ---- | ----------------------------- | -------------------------------------------------------------------------------------------------- |
| HIGH | `anthropic/claude-opus-4-8`   | architect, plan-reviewer, refactor-planner                                                         |
| MID  | `anthropic/claude-sonnet-4-6` | orchestrator, product-manager, backend, frontend, ui, db, api, code-reviewer, frontend-error-fixer |
| LOW  | `anthropic/claude-haiku-4-5`  | qa, gatekeeper, web-research-specialist                                                            |

> **Note:** lint/security scanning used to run on a separate Haiku-tier `linter`
> agent; it's now Stage 1 of `code-reviewer` (Sonnet-tier), since the two were
> already duplicating the static-analysis step. Net effect: one fewer agent
> hop and one fewer LLM call per PR, at the cost of running the lint stage on
> the pricier model. For most PRs this is a net win; if lint-tool cost becomes
> a concern, splitting lint back out to a Haiku-tier agent is a one-file change.

---

## Agent and skill trigger reference

Understanding what fires automatically vs what you control is important for working
with the framework efficiently. Everything listed as automatic happens without any
action from you — just open a project and start a task.

### Agents

| Agent                                        | Trigger                     | When                                                                                      |
| -------------------------------------------- | --------------------------- | ----------------------------------------------------------------------------------------- |
| `orchestrator`                               | **Automatic**               | Entry point — fires on every task                                                         |
| `product-manager`                            | **Automatic**               | Orchestrator routes here on every task start                                              |
| `architect`                                  | **Automatic**               | After spec is confirmed by developer                                                      |
| `plan-reviewer`                              | **Automatic**               | After every HLD — before any implementation                                               |
| `backend` / `frontend` / `ui` / `db` / `api` | **Automatic**               | Orchestrator routes based on task scope                                                   |
| `code-reviewer`                              | **Automatic**               | After every implementation step (lints, scans, then reviews)                              |
| `qa`                                         | **Automatic**               | After code review passes                                                                  |
| `gatekeeper`                                 | **Automatic**               | Final gate before every handoff                                                           |
| `frontend-error-fixer`                       | **Automatic** (conditional) | Only when a frontend error is present                                                     |
| `refactor-planner`                           | **You trigger**             | When you explicitly decide to plan a refactor                                             |
| `web-research-specialist`                    | **You trigger**             | Rule 12 (isolated environment) — ask the orchestrator "search the web for X?" and confirm |

### Skills — always-load (fire on every task)

| Skill                           | Who loads it                          |
| ------------------------------- | ------------------------------------- |
| `agent-guidelines`              | Every agent                           |
| `surgical-changes`              | Every implementation agent            |
| `project-overview/sub/stack.md` | Every agent                           |
| `code-standards`                | Implementation agents + code-reviewer |
| `static-code-analysis`          | Linter + code-reviewer (as precheck)  |

### Skills — automatic conditional (fire when conditions are met)

| Skill                        | Condition                                                                                                                                                                                |
| ---------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `first-run-analysis`         | `project-overview` is empty or contains `[XXX]`                                                                                                                                          |
| `zoom-out`                   | First session on a project (after first-run) or long gap between sessions                                                                                                                |
| `repo-topology`              | During first-run analysis or any cross-service task                                                                                                                                      |
| `graphify`                   | Loaded by `zoom-out`, `first-run-analysis`, `pattern-enforcement` whenever `graphify-out/graph.json` exists; also fires directly on "what calls X" / "what depends on X" style questions |
| `build-verify`               | Loaded by `backend`, `frontend`, `frontend-error-fixer`, `api`, `db`, `ui` — always runs before any of them declares work done, not conditional                                          |
| `diagnose`                   | Task type is a bug fix                                                                                                                                                                   |
| `tdd`                        | Writing code for a feature or fix                                                                                                                                                        |
| `grill-me`                   | Requirements or design are ambiguous                                                                                                                                                     |
| `pattern-enforcement`        | Writing any file in a new domain or module                                                                                                                                               |
| `third-party-policy`         | Any dependency is being added, removed, or updated                                                                                                                                       |
| `atomic-changes`             | Any task involving a PR breakdown                                                                                                                                                        |
| `branching-policy`           | Any task that writes files                                                                                                                                                               |
| `localization`               | Task involves UI text, strings, or CSS layout                                                                                                                                            |
| `api-contracts`              | API contract or 3rd party integration work                                                                                                                                               |
| `db-patterns`                | Database work detected                                                                                                                                                                   |
| `domain-model`               | Unfamiliar domain terminology encountered                                                                                                                                                |
| `documentation`              | After changes that affect architecture or API                                                                                                                                            |
| `git-hooks`                  | During first-run analysis                                                                                                                                                                |
| `clean-code-*` skills        | Based on file types in the diff (code-reviewer loads selectively)                                                                                                                        |
| `clean-code-security`        | Any code touching auth, input, persistence, or external APIs                                                                                                                             |
| `platform-guard`             | Capacitor project + React-vs-native decision needed                                                                                                                                      |
| `capacitor-bridge`           | Capacitor plugin or platform-specific code in diff                                                                                                                                       |
| `readability-cognitive-load` | Any implementation or review task                                                                                                                                                        |
| `linting-tools`              | Linter agent always loads it                                                                                                                                                             |
| `testing-strategy`           | QA agent always loads it                                                                                                                                                                 |
| `xray-scanning`              | Linter agent always loads it                                                                                                                                                             |

### Skills — auto-triggered by context budget (Rule 14)

These fire automatically when session length exceeds thresholds —
no action needed from you:

| Skill     | Threshold                                                  |
| --------- | ---------------------------------------------------------- |
| `caveman` | > 8 orchestrator responses OR any response > ~3,000 tokens |
| `handoff` | Same — fires together with `caveman`                       |

### Skills — you trigger (human-invoked)

These only fire when you explicitly ask for them.
Use them as slash commands (`/` prefix in OpenCode/Claude Code)
or by telling the orchestrator directly:

| Skill / Command                   | How to invoke                                | What it does                                                                          |
| --------------------------------- | -------------------------------------------- | ------------------------------------------------------------------------------------- |
| `excalidraw-sequence-diagram`     | "Draw a sequence diagram for X"              | Creates Excalidraw JSON for service flows                                             |
| `improve-codebase-architecture`   | "Review the architecture" or `/arch-review`  | Finds shallow-to-deep module opportunities                                            |
| `refactor-planner` (agent)        | "Plan a refactor of X"                       | Safe incremental refactor plan before any code changes                                |
| `web-research-specialist` (agent) | "Search the web for X"                       | External research — requires your explicit confirmation (Rule 12)                     |
| `caveman`                         | "Be brief" / "caveman mode"                  | Compressed output — also fires automatically at budget threshold                      |
| `handoff`                         | "Handoff" / `/handoff`                       | Session compact — also fires automatically at budget threshold                        |
| `zoom-out`                        | "Zoom out" / "orient me"                     | Orientation map — also fires automatically on first session                           |
| `first-run-analysis`              | "Re-scan the project"                        | Manual refresh of project-overview (auto-fires on `[XXX]`)                            |
| `repo-topology`                   | "Detect the topology"                        | Manual topology re-detection (auto-fires during first-run)                            |
| `graphify`                        | "What calls X?" / "How does A connect to B?" | Queries the code knowledge graph instead of grepping — see `skills/graphify/SKILL.md` |

---

| Problem                                                          | Fix                                                                                                                                                                                                                                                                                                          |
| ---------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `python: command not found`                                      | Try `python3 setup.py` instead                                                                                                                                                                                                                                                                               |
| `WinError 1314` / `Permission denied` on file symlinks (Windows) | Setup doesn't need admin rights or Developer Mode — it auto-falls back to copying those files instead. This just means they won't auto-update on `git pull`; re-run `python setup.py` after pulling, or ask IT to enable Developer Mode (`Settings → System → For developers`) for live-linked files instead |
| After `git pull` files seem stale (Windows copy mode)            | Re-run `python setup.py` — copies don't auto-update like symlinks. Run `python setup.py --verify` anytime to check without changing anything                                                                                                                                                                 |
| `gh` not found                                                   | Not required — the framework still pushes your branch and tells you to open the PR manually. Install later from https://cli.github.com if you want the auto-open behavior, then `python setup.py --verify` to confirm it's picked up                                                                         |
| Not sure what still needs attention                              | Run `python setup.py --verify` — prints a read-only "Action required" summary, nothing is changed                                                                                                                                                                                                            |
| Tool shows "not found" but is installed                          | Restart your terminal (PATH needs to refresh), then re-run setup                                                                                                                                                                                                                                             |
| VS Code Copilot has no instructions                              | Re-run `python setup.py` — it updates `settings.json` automatically                                                                                                                                                                                                                                          |
| Skills not loading                                               | Verify `~/.config/opencode/skills` or `~/.claude/skills` exists                                                                                                                                                                                                                                              |
| RTK download failed                                              | Install manually: https://github.com/rtk-ai/rtk/releases                                                                                                                                                                                                                                                     |
| Token Optimizer not installing                                   | See "Token usage reduction" section above                                                                                                                                                                                                                                                                    |
| Graphify not installing                                          | Install manually: `uv tool install graphifyy` (or `pipx install graphifyy`), then re-run `python setup.py`                                                                                                                                                                                                   |
| `graph.html` too large / slow to open                            | Use `scripts/graphify-smart-viz.sh` instead of raw `graphify` — it skips HTML generation past ~5000 nodes automatically                                                                                                                                                                                      |
| Git hooks not firing                                             | Run `git init` in your existing repo to apply the template                                                                                                                                                                                                                                                   |
