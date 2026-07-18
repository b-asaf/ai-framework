# Token & model monitoring

Two tools, answering two genuinely different questions. Neither reimplements
the other, and — important distinction — **they don't overlap even though
they sound similar.**

## 1. `ccusage` — how many tokens, which models, across every tool you use

Wired in by `setup.py` (`install_ccusage`). Reads local usage logs directly —
no API key, nothing uploaded — from **whichever coding tool you actually
used**: Claude Code, Codex CLI, OpenCode, Gemini CLI, GitHub Copilot CLI.
Same command family regardless of which tool you picked that day, which is
the actual ask: monitoring that supports any tool installed, the same way
this framework does.

```bash
# Zero-install, always works:
npx ccusage@latest daily

# If setup.py installed it globally, just:
ccusage daily      # today, all detected tools combined
ccusage weekly      # this week
ccusage monthly     # this month
ccusage session      # per-session — the closest thing to "current task"
ccusage session --json   # for scripting

# Scoped to one tool specifically, if you want that instead of the combined view:
ccusage claude daily
ccusage opencode weekly
ccusage codex daily
ccusage gemini daily
ccusage copilot daily
```

This answers:
- **How many tokens did the current task use?** → `ccusage session` — your
  most recent session is the top row.
- **Which models were used?** → every report includes a `models`/`modelsUsed`
  list; `ccusage daily --breakdown` gives a full per-model cost split.
- **24h/week/month totals?** → `daily` / `weekly` / `monthly` natively.

### Known gap: Copilot IDE extensions

`ccusage`'s Copilot support is for the standalone **Copilot CLI**, not the
IntelliJ/VS Code IDE extensions this framework also wires into. IDE-extension
usage lives in GitHub's org-level billing dashboards, not a local log file —
there's no local source to read for that one. If most of your Copilot usage
is through the CLI, you're covered; through the IDE plugins, you're not.

## 2. `model-policy-check.js` — did the right agent use the right model

This is **not** something `ccusage` can answer, and it's not a limitation of
`ccusage` — `ccusage`'s `agent` field (where present) means "which coding
tool" (`claude`, `codex`, `opencode`), not "which agent *within* your
OpenCode setup" (`backend`, `qa`, `code-reviewer`...). Those are different
concepts. Only `opencode-usage` (also wired by `setup.py`,
`install_opencode_usage`) reads OpenCode's own per-agent session metadata —
that's why this script stays on it instead of moving to `ccusage`.

```bash
node monitoring/model-policy-check.js               # last 7 days
node monitoring/model-policy-check.js --since 24h
node monitoring/model-policy-check.js --since 30d
```

Reads each agent's expected model straight from its own `agents/*.md`
frontmatter — no separate policy table to drift out of sync. See the script
header for details; example output further down in this repo's CHANGELOG.

By construction, this only covers OpenCode — the only tool in this framework
where "per-agent model" is even a concept `ccusage` would have data for. For
Claude Code/Codex/Gemini/Copilot, the whole session runs on one model the
developer picked; there's no per-agent policy to check.

## Which one do I run?

- Want to know if you're burning too many tokens this week, on whichever
  tool you happened to use? → `ccusage weekly`
- Want to know if `code-reviewer` quietly ran on Sonnet-tier cost when it
  should've been on Haiku? → `node monitoring/model-policy-check.js`

Both are safe to run anytime — read-only, local data only, no network calls
beyond `ccusage`'s optional pricing-data fetch (use `--offline` to skip that
too).
