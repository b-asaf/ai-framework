# Decision: Cross-platform Python wrapper for graphify, auto `--code-only` detection

**Date:** 2026-08-14
**Status:** accepted

## Context
Running graphify in real project surfaced two real problems, both confirmed by direct
evidence, not assumption:

1. `graphify extract .` failed with "no LLM API key found" — the corporate environment
   uses GitHub Copilot's proxy for model access, not raw provider API keys, so none of
   graphify's expected env vars (`ANTHROPIC_API_KEY` etc.) are set. Confirmed fix: `--code-
   only` skips semantic extraction of doc/image files entirely, needs no key, and covers
   what's actually needed (code call/import graph).
2. `scripts/graphify-smart-viz.sh` requires `bash`. Confirmed via direct testing: `wsl` on
   this machine failed with `"The .wslconfig setting 'wsl2.nestedVirtualization' is disabled
   by the computer policy"` — WSL itself is blocked by corporate IT policy, not just absent.

Separately, `graphify --help` was checked directly (not assumed) to confirm a real `--out
DIR` flag exists on `extract`, writing to `<DIR>/graphify-out/` instead of `<path>/graphify-
out/`. `cluster-only` has its own independent default location that does not know about a
custom `--out` used during extract.

## Options considered
- A: Document the manual `--code-only` flag and manual multi-command workaround for
     Windows/WSL-blocked users — cheapest, but leaves the same failure mode for every
     future project until someone remembers the workaround
- B: Fix `graphify-smart-viz.sh` to detect Windows and shell out differently — still
     requires *some* POSIX-like shell to exist, doesn't solve the WSL-blocked-by-policy case
- C: Rewrite the wrapper in Python — chosen. `setup.py` already requires Python on every
     machine running this framework, so this removes the bash/WSL dependency entirely
     rather than working around it.

## Decision: Option C
`scripts/graphify_smart_viz.py` added, kept alongside (not replacing) the existing `.sh` for
environments where `bash` is available and preferred. It: (1) auto-detects whether any LLM
API key env var is set and adds `--code-only` automatically if not, (2) always runs
clustering regardless of repo size, only conditionally skipping the HTML visualization past
the node threshold, (3) correctly propagates a custom `--out` location to `cluster-only`'s
`--graph` flag explicitly, since that command's own default does not account for it.

`skills/graphify/SKILL.md` updated to point to the Python script as the primary/recommended
tool, document the auto `--code-only` behavior, and document the confirmed `--out` flag.

## Reasoning
1. Agent or deterministic? Fully deterministic — environment detection (env vars present or
   not, node count over/under threshold) via plain code, zero LLM judgment involved.
2. Trade-off: maintaining two wrapper scripts (`.sh` and `.py`) instead of one — accepted
   because the alternative (Python-only) would regress the experience for `bash`-native
   environments where the shell version already works fine.
3. Cheaper alternative: none simpler than removing a hard dependency (bash/WSL) that's
   already confirmed blocked in at least one real environment.
4. Visibility gained: the "no LLM API key found" failure and the WSL-policy-blocked failure
   are now both handled automatically rather than requiring a developer to rediscover the
   same fix on every new project.

## Consequences
- Any future documentation or onboarding referencing `graphify-smart-viz.sh` as *the* way to
  build the graph should be updated to mention `graphify_smart_viz.py` as the cross-platform
  default, per the `SKILL.md` change above.
- The auto `--code-only` detection means a developer who *does* have a real provider API key
  configured (not just Copilot-proxy access) will still get full semantic extraction
  automatically — this only changes behavior when no key is present, not a blanket policy
  against using one.
- If graphify's own CLI changes `cluster-only`'s default resolution behavior in a future
  version to account for `--out` automatically, the explicit `--graph` pass-through in the
  Python script becomes redundant but not harmful — worth revisiting if graphify's own
  changelog ever mentions this.