---
name: pr-provider
description: Pushes the current branch and opens a draft PR/MR on GitHub, GitLab, or Azure DevOps by running the deterministic script `scripts/open-draft-pr.py` — provider detection, API calls, and response parsing all happen in code, not in the model. Loaded by the orchestrator as part of AGENTS.md Check 4 / Step 10 (Handoff).
---

## Quick reference

- **Run the script — never compose `git push`, `curl`, or JSON yourself.**
  ```
  python "$env:USERPROFILE\.config\opencode\scripts\open-draft-pr.py" --title "<type(scope): description>" --body "<short summary>"
  ```
  (macOS/Linux: `python3 ~/.config/opencode/scripts/open-draft-pr.py ...`)
- `--branch`, `--base`, `--title`, `--body` are all optional; when omitted the script derives them from git (current branch, `origin/HEAD`, last commit subject/body). Use `--body-file <path>` for multi-line bodies.
- The script does the push itself. Do **not** run `git push` separately.
- Read the script's output, not your own assumptions: the result is the `STATUS:` line and the exit code.

## What the script does (so you can explain it, not redo it)

1. Refuses to run on `main`/`master`/the base branch (exit 2).
2. Detects the provider from `git remote get-url origin`: `github.com` → GitHub; `dev.azure.com`, `*.visualstudio.com`, or any remote whose path contains `/_git/` (Azure DevOps Server / TFS on-prem) → Azure DevOps; host containing `gitlab` → GitLab. Anything else (e.g. a self-hosted GitLab whose host name doesn't say so) is set once per repo: `git config ai-framework.provider <github|gitlab|ado>`. Azure DevOps Server's REST API version is negotiated automatically (7.1 → 7.0 → 6.0 → 5.1); pin one with `git config ai-framework.adoApiVersion 6.0`.
3. Pushes the branch (never `--force`).
4. Opens the PR/MR **as a draft** and verifies the server's response really says draft: GitLab via `git push` options (no token), GitHub via REST with `GITHUB_TOKEN` (or `GH_TOKEN`), Azure DevOps via REST with `ADO_PAT` (or `AZURE_DEVOPS_EXT_PAT`).

## Interpreting the result

| Exit | `STATUS:` | What to tell the developer |
|---|---|---|
| 0 | `DRAFT_PR_OPENED` | Report the `URL:` — this is the normal success notification (AGENTS.md Check 4, item 5). |
| 0 | `PR_ALREADY_EXISTS` | The branch is pushed and a PR/MR already exists; nothing new was created. Say so; give the `URL:`. |
| 10 | `PUSHED_MANUAL_PR_NEEDED` | Branch is pushed but no PR/MR was opened. Relay `REASON:` verbatim and give the `URL:` (a ready-made "create PR" link). Typical cause: token/PAT env var not set, or an unrecognized host. |
| 5 | `PR_OPENED_NOT_DRAFT` | A PR was created but the server did **not** make it a draft (some servers ignore the flag). Tell the developer plainly, give the `URL:`, and ask them to convert it to a draft or abandon it. Do not open another one. |
| 4 | `API_FAILED` | Branch is pushed; the provider rejected the request. Relay `REASON:` and give the manual `URL:`. Do not retry blindly. |
| 1 | `PUSH_FAILED` | Nothing was pushed. Relay `REASON:` (e.g. no `origin` remote). |
| 2 | `USAGE_ERROR` | The script refused to run (e.g. on `main`). Fix the cause; do not work around it. |

## Rules

- Never ask the developer to paste a token into chat. Missing credentials are fixed by them setting an environment variable in their own shell; the script already tells you which one.
- Never echo, log, or include a token/PAT value in any message. The script never prints one.
- Never mark the PR/MR ready-for-review or merge it — the script only ever opens drafts.
- Never bypass the script with a hand-written `git push` / `curl` / provider CLI call to "get around" a non-zero exit. If the script cannot do it, report why and stop.
- If the script itself is missing or crashes (not a `STATUS:` result), stop and tell the developer — `python setup.py --verify` re-links the framework's `scripts/` directory.