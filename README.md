# Manual

## Installation
Install OpenCode: `npm install -g opencode-ai`

## Configuration
Connect to GitHub via CMD:
- `opencode auth login`
  - Select provider: "Github Copilot"
  - Select deployment type: "Github.com"
  - Connect to Rafael GitHub
- Open in **Edge** the URL that is in the CMD and paste the code

  **OR**

  [Follow the tutorial](https://rafaelcoil.sharepoint.com/:u:/r/sites/GitHubCopilot/SitePages/%D7%9E%D7%93%D7%A8%D7%99%D7%9A-%D7%94%D7%AA%D7%A7%D7%A0%D7%94.aspx?csf=1&web=1&e=Ws8sil)

- Validate that `login` succeeded

##### Optional
OpenCode Desktop (if CLI is not your tool):
Download OpenCode desktop app: https://opencode.ai/download
Or use the installation that is in the folder

---

## How to use in a project

### Option A — Installer script (recommended)

Run this from your workspace root (the folder that contains all your repos):

```bash
bash install.sh
```

Or if you want the framework available across **all projects** on your machine:

```bash
bash install.sh --global
```

The script will:
- Copy all agents, skills, and config files into the right places
- Replace `[XXX]` in `_opencode.json` with your actual project name
- Attempt to install git hooks in any repo it finds
- Print a checklist of what to do next

> **That's it.** Skip to [First-run analysis](#first-run-analysis-automatic) below.

---

### Option B — Manual setup

If you prefer to set up manually:

#### Step 1 — Set up the workspace

**Option A — Automated installer (recommended)**

Run this from your workspace root (the folder that contains all your repos):

```bash
# From a local clone of the framework:
bash install.sh

# OR directly from GitHub (no clone needed):
curl -fsSL https://raw.githubusercontent.com/your-org/your-framework/main/install.sh | bash
```

The installer copies all framework files, replaces `[XXX]` with your project name automatically, installs git hooks in any repos it finds, and prints a checklist of what to do next. Skip to [Step 3](#step-3) after running it.

**Option B — Global install (all projects on this machine)**

```bash
bash install.sh --global
# OR:
curl -fsSL https://raw.githubusercontent.com/your-org/your-framework/main/install.sh | bash -s -- --global
```

**Option C — Manual copy**

Copy the framework files into your workspace root alongside your repos. All repositories must be in the same root folder:

```
[workspace]/[project folder]
├── _opencode.json          ← from the framework
├── AGENTS.md               ← from the framework
├── workflow-guide.md       ← developer guide
├── Manual.md               ← this file
├── docs/
│   └── refactoring-plan.md ← generated on first run if issues found
├── .opencode/
│   ├── agents/             ← all agent .md files
│   └── skills/             ← all skill folders
├── [XXX]-be/               ← your backend repo
└── [XXX]-fe/               ← your frontend repo
```

> For microservice projects, there may be multiple BE repos alongside `[XXX]-fe/`. The first-run analysis will detect this and configure the workspace accordingly.

---

#### Installer details

`install.sh` does the following automatically:
- Copies `.opencode/agents/` and `.opencode/skills/` into the workspace
- Copies `AGENTS.md`, `workflow-guide.md`, `Manual.md`, `_opencode.json`, `docs/`
- Replaces `[XXX]` in `_opencode.json` with the current folder name
- Installs git hooks (`pre-commit`, `commit-msg`, `pre-push`) in any git repos it finds in subdirectories
- Prints a checklist of remaining steps

If the automated hook install fails, run manually in each repo:
```bash
bash scripts/hooks/install-hooks.sh
```

#### Step 2 — Replace `[XXX]` in `_opencode.json`

> **If you used the installer (Option A/B above), this was done automatically. Skip to Step 3.**

Open `_opencode.json` in your editor and replace every `[XXX]` with your actual project name:

```json
"name": "myproject-Project",
"path": "./myproject-be",
"path": "./myproject-fe"
```

#### Step 3 — Start opencode from the workspace root {#step-3}

> ⚠️ **opencode must be started from the folder that contains `_opencode.json` — not from inside either repo.**

CLI:
```bash
cd workspace/
opencode
```

Desktop app: open the `workspace/` folder (not a repo subfolder).

---

## First-run analysis (automatic)

The first time you open a project in opencode, the orchestrator automatically performs a full first-run analysis **before accepting any task**. This cannot be skipped.

### What it does

| Step | What happens |
|---|---|
| 1. Topology detection | Scans for microservice signals (Docker Compose, Kubernetes, multiple services). Asks you to confirm. Updates `_opencode.json` accordingly. |
| 2. Repo state detection | Determines if each repo is new, partially implemented, or mature. |
| 3. Language & tool detection | Detects language, framework, build tool, test framework, linter, database, API style per repo. |
| 4. Convention detection | Scans representative files to discover patterns: test placement, naming, error handling, layer structure. |
| 5. Convention evaluation | Evaluates detected conventions against Clean Code, SOLID, KISS, and YAGNI. Flags violations. |
| 6. Refactoring plan | If violations or inconsistencies are found, generates `docs/refactoring-plan.md`. No changes are made automatically. |
| 7. File updates | Updates `project-overview`, `_opencode.json`, `workflow-guide.md`, and this `Manual.md` with project-specific findings. |

### What you need to do during first-run

The orchestrator will ask you **two questions** that require your input:

1. **"Is this a microservice architecture?"** — Confirm or correct the preliminary assessment.
2. **Approval of findings** — Confirm that the detected stack and conventions are correct before agents start enforcing them.

Everything else is automatic.

### Outputs after first-run

| File | What it contains |
|---|---|
| `.opencode/skills/project-overview/SKILL.md` | Full project context: topology, stack, conventions, patterns |
| `_opencode.json` | Updated with actual project name and topology-appropriate agent paths |
| `docs/refactoring-plan.md` | Refactoring recommendations (only if issues found) |
| `workflow-guide.md` | Project-specific notes appended (only if relevant) |

---

## Ongoing use

After first-run, describe any task in plain language. The agents handle the rest.

**Tips for best results:**
- Be specific about what's broken and how to reproduce it
- One task per session — don't mix unrelated requests
- Review the diff before committing — you are the last gate
- Read `workflow-guide.md` for the full day-to-day guide

---

## Quick checklist

- [ ] opencode CLI installed and authenticated
- [ ] All repos are cloned and accessible locally
- [ ] You're running opencode from the workspace root (not inside a repo)
- [ ] `[XXX]` replaced in `_opencode.json` (done automatically by `install.sh`)
- [ ] First-run analysis completed and confirmed
- [ ] `docs/refactoring-plan.md` reviewed (if generated)
- [ ] Git hooks installed in both repos (done automatically by `install.sh`)

---

## Troubleshooting

| Problem | Solution |
|---|---|
| `install.sh` permission denied | Run `chmod +x install.sh` then `bash install.sh` |
| `install.sh` curl fails | Clone the repo locally and run `bash install.sh` |
| `[XXX]` still in `_opencode.json` after install | Installer couldn't detect folder name — replace manually |
| Agents don't know the project stack | First-run analysis may not have completed — check `project-overview` for `[XXX]` placeholders |
| `_opencode.json` not detected | Make sure opencode is opened from the workspace root, not a repo subfolder |
| Skills not found | Verify `.opencode/skills/` exists and contains skill folders — re-run `bash install.sh` if missing |
| Microservice agents missing | First-run topology step may have detected monolith — re-run analysis or manually add sub_agents to `_opencode.json` |
| Refactoring plan not generated | No violations detected — check `project-overview` for convention findings |
| Git hooks not enforcing | Run `bash scripts/hooks/install-hooks.sh` in each repo root (see `git-hooks` skill) |