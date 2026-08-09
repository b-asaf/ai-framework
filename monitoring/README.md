# Token & model monitoring

## `ccusage` — how many tokens, which models, across every tool you use

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

Safe to run anytime — read-only, local data only, no network calls beyond
`ccusage`'s optional pricing-data fetch (use `--offline` to skip that too).
