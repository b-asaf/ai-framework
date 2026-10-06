# Git permission evidence (step 0.6)

Date: 2026-10-03. Model: github-copilot/gpt-5.6-terra. OpenCode version: 1.18.34.

Setup: throwaway repo with a local bare remote. Framework hooks installed through the git template. Agents: `git-test` (section 6 rules, catch-all first), `probe-test` (catch-all, one allow, one deny), `noperm-test` (inherits the global config).

## Results

| Test | Expected | Result |
|---|---|---|
| 1. branch and commit, no prompt | pass | pass. Commit `chore: add test note` on `chore/git-test-one`. Headless "ask" is auto-rejected, so success means no prompt was needed |
| 2. push feature branch, no prompt | pass | pass. `origin/chore/git-test-one` at 688e045 |
| 3. agent pushes main and force pushes | blocked | the agent refused both commands on `AGENTS.md` instructions without running them, so the deny rules were not exercised by this command |
| 3 (probe). deny after a catch-all | enforced | `git tag probe-allow-one` ran; `git tag probe-deny-one` was blocked with a rule list. The permission layer enforces denies placed after `"*": "ask"` |
| 3b. `git push origin HEAD:main` by hand, no `origin/HEAD` | blocked | NOT blocked. The hook warned, skipped branch protection and the verify gate, and the push moved remote main bfddbfc to 688e045 |
| 3b retest, `origin/HEAD` set | blocked | blocked: "Direct push to 'main' is not allowed". Remote main stayed at 688e045 |
| 4. `npm install lodash` | not silent | `permission requested; auto-rejecting`. No `package.json` or `node_modules` |
| 7. global config, `git checkout -b` by an agent with no bash rules | allowed by the global allow | rejected: `permission requested; auto-rejecting`. Branch unchanged |

## Findings

- F9 verified: the global `opencode.json` bash block lists the git allows, then the git denies, then `"*": "ask"` last. The catch-all overrides the allows (and most likely the denies), so a headless agent inheriting the global config cannot branch, commit or push. Decision #3: move the catch-all first.
- In headless runs an `ask` is auto-rejected, so it behaves like `deny`.
- The rule dump shows `* allow *` first, then the global rules, then the agent's own rules. Last match wins.
- The pre-push `branch_protection` check fails open: without `origin/HEAD` or `protectedBranches` in `.ai-framework.json` it warns and allows the push. The verify gate also skips when `.ai-framework.json` is missing.
- The global config under `~/.config/opencode/` links into `/d/ai-framework` (`opencode.json`, `AGENTS.md`, `agents`, `commands`, `hooks`, `scripts`, `skills`). A `git pull` on main changes live behavior.

## Not tested

- The literal pattern `git push*main*` (also likely to match branches such as `chore/maintenance-note`).
- Manifest change without a `Dependency-Approved:` trailer (needs the 3A check).
- New task on an existing branch asks the developer (needs the 1.9 `AGENTS.md` rule).
- The interactive prompt for `npm install` (only headless auto-reject was observed).
