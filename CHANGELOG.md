# Changelog

All notable changes to ai-framework are documented here.
Format: [version] — [date] — [summary]

Changes are made on `develop` branch and merged to `main` when stable.

---

## Unreleased (develop)

## v1.1.0 — agent consolidation, monitoring, install reliability

- **Added cross-tool token monitoring (`ccusage`).** Wired into `setup.py`
  (`install_ccusage`) alongside `opencode-usage` (`install_opencode_usage`),
  not replacing it — they answer different questions. `ccusage` reads local
  usage logs from Claude Code, Codex CLI, OpenCode, Gemini CLI, and Copilot
  CLI, giving one command family (`ccusage daily/weekly/monthly/session`)
  across whichever tool a developer actually used that day. `opencode-usage`
  stays as the engine behind `monitoring/model-policy-check.js`: it's the
  only one that reads OpenCode's own per-agent metadata — `ccusage`'s
  `agent` field means "which coding tool," not "which OpenCode subagent"
  (verified against ccusage's actual `--json` output before wiring; these
  were initially assumed interchangeable, corrected before implementing).
  Known gap, documented in `monitoring/README.md`: `ccusage`'s Copilot
  support covers the Copilot CLI, not the IntelliJ/VS Code IDE extensions
  this framework also wires into.
- **Added `monitoring/model-policy-check.js`** — cross-references actual
  per-agent model usage against each agent's own `model:` frontmatter
  declaration (no separate policy table to keep in sync). Tested end-to-end
  against a mocked `opencode-usage` output including a deliberate mismatch
  case; correctly flagged it and cleared the rest.
- **Added `ci/review.js`** — headless CI code-review runner (Stage 1:
  prints a structured verdict to stdout + a log file; hand-paste into your
  PR/MR for now). Runs the same checklist as `agents/code-reviewer.md`,
  loading its declared skills directly rather than reimplementing them, with
  one addition: checklist items that assume a spec/HLD from the interactive
  `/task` flow are explicitly treated as N/A in headless mode instead of
  failing. No `@gatekeeper` step (validates against task-flow state that
  doesn't exist for an arbitrary PR) and no branch guard (nothing to guard
  in CI). Zero npm dependencies — native `fetch`, Node 18+. Stage 2
  (auto-post via `gh pr comment` / GitLab's notes API) sketched at the
  bottom of the file, not wired yet.

- **Dropped Cursor and Windsurf support.** They were never actually wired by
  `setup.py` (not in `detect()` or `build_links()` at all) — `CURSOR.md` and
  `WINDSURF.md` were dead files nothing ever installed. Deleted both, along
  with `SHARED.md`/`SHARED-reference.md` (their only real consumers besides
  an also-unused `instructions/wrappers/` folder — every live tool integration
  already points straight at root `AGENTS.md`/`AGENTS-reference.md`). Net:
  4 files + 1 folder removed, zero functional change, one less place for
  rules to silently drift out of sync (this is what caused the linter
  references to go stale in `SHARED.md` before being caught above).

- **Agent consolidation:** merged `linter` into `code-reviewer` (16 → 15 agents).
  `code-reviewer` now runs lint/security detection as Stage 1, then review as
  Stage 2, in one pass — removes a duplicate `static-code-analysis` invocation
  that both agents were separately running. Updated: `orchestrator.md` (Steps
  6-7 merged), `gatekeeper.md`, `AGENTS.md` Rule 9, `AGENTS-reference.md`,
  `SHARED.md`/`SHARED-reference.md`, `commands/review.md`, `commands/task.md`,
  `CURSOR.md`, `WINDSURF.md`, and the skills that referenced the linter agent
  by name (`static-code-analysis`, `linting-tools`, `xray-scanning`, `caveman`,
  `project-overview/sub/tooling.md`). Tradeoff: lint/security scanning now runs
  on `code-reviewer`'s Sonnet tier instead of the old Haiku-tier `linter` —
  fewer agent hops, slightly higher per-PR cost on that step.
- **Fixed double skill-routing:** `skill-rules.json` (fuzzy keyword/intent
  matching) and each agent's own hardcoded "Always load" list were both firing
  inside the structured task flow, stacking skills on top of each other.
  `skill-rules.json` is now explicitly scoped to ad-hoc/off-workflow requests
  only (AGENTS.md/SHARED.md Rule 8 rewritten); inside `/task`, each agent's own
  list is sole authority. Added `$config.maxMatchesPerRequest: 3` (priority-
  ordered cutoff) to `skill-rules.json` for the ad-hoc case.
- **Removed the redundant task-type skill-routing table** from
  `AGENTS-reference.md` and `SHARED-reference.md` — it duplicated
  `skill-rules.json` (which itself says it was meant to replace that table;
  the replacement was never finished until now).
- **Removed Headroom** — dropped from the token-reduction stack (now RTK +
  Token Optimizer only). Removed `install_headroom()`/`wire_headroom()` from
  `setup.py`, its row from the README token-reduction table, and its
  troubleshooting entry.
- **`setup.py` no longer requires admin rights / UAC elevation.** Removed
  `_enable_developer_mode_windows()` (registry write + UAC-elevated
  PowerShell attempt) — corporate/locked-down machines were failing exactly
  where this ran. File symlinks silently fall back to copies as before; the
  script no longer tries to fix that itself.
- **`gh` CLI: detect-only, no auto-install.** Removed the `brew`/`winget`
  install attempts (`install_gh()` → `check_gh()`) — same reasoning as above.
  The framework already degrades gracefully without `gh` (AGENTS.md Check 4:
  push, then open the PR manually).
- **Added `python setup.py --verify`** — read-only status check (symlink/copy
  drift via content hash, `gh` presence) that can be re-run anytime without
  touching any files.
- **Added a single "Action required" summary block** at the end of setup
  output — anything the developer needs to do themselves (missing `gh`,
  no symlink privilege, stale copies) is now collected and printed once,
  instead of scattered mid-log warnings that were easy to miss.
- Deleted `enable-dev-mode.ps1` (dead file, no longer called).
- Per-agent model tiers (Opus/Sonnet/Haiku based on task complexity)
- Token monitoring: opencode-tokenscope, opencode-usage wired via setup.py
- Guarded commit/push/PR flow (Check 4 in AGENTS.md)
- Rule 14: auto-trigger caveman + handoff at context budget threshold
- 8 skills set to disable-model-invocation: true
- Quick reference sections on all skills > 40 lines
- All agents load project-overview sub-files selectively
- Token reduction stack: RTK + Token Optimizer

## v1.0.0 — initial stable baseline

- 16 agents, 39 skills, 4 slash commands
- OpenCode as primary tool, global wiring via setup.py
- AGENTS.md with 14 rules (XML-tagged)
- Per-agent model tiering
- Branching policy enforced via Check 2
- Post-implementation pipeline: linter → code-reviewer → qa → gatekeeper
- session-end.js hook for auto session summary
