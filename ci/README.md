# CI code review (Stage 1)

Headless version of `@code-reviewer` — no developer session, no branch guard,
no `@gatekeeper` (that validates against a spec/HLD from the interactive
`/task` flow, which doesn't exist for an arbitrary PR). Same checklist, same
skills, same output format. Prints to stdout and saves to `ci/reports/`.

## Setup

Requires Node 18+ and `git`. No `npm install` — zero dependencies, uses
native `fetch`.

```bash
export ANTHROPIC_API_KEY=sk-...
```

## Usage

```bash
# Review the diff between two refs (typical CI usage: base=target branch, head=PR branch)
node ci/review.js --base main --head HEAD

# Review a raw diff file instead (e.g. piped from your CI system)
node ci/review.js --diff change.diff

# See exactly what would be sent, without calling the API or spending tokens
node ci/review.js --base main --head HEAD --dry-run

# Report only, never fail the CI job on REQUEST CHANGES
node ci/review.js --base main --head HEAD --no-fail

# Pass PR context for a better review
node ci/review.js --base main --head HEAD --title "Add CSV export" --desc "Fixes #123"
```

## Exit codes

- `0` — APPROVED / APPROVED WITH ADVISORY NOTES (or `--no-fail` was set)
- `1` — REQUEST CHANGES
- `2` — the script itself failed (missing API key, git error, etc.) — distinct
  from `1` so CI can tell "review found problems" apart from "review didn't run"

## GitHub Actions example

```yaml
- run: node ci/review.js --base ${{ github.event.pull_request.base.ref }} --head ${{ github.sha }}
  env:
    ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
```

## GitLab CI example

```yaml
review:
  script:
    - node ci/review.js --base $CI_MERGE_REQUEST_TARGET_BRANCH_NAME --head $CI_COMMIT_SHA
  variables:
    ANTHROPIC_API_KEY: $ANTHROPIC_API_KEY
```

Both just print the report as a job log right now — copy/paste into the PR/MR.
Auto-posting (Stage 2) is sketched at the bottom of `review.js` once you're
happy with output quality and ready to wire it to `gh pr comment` or GitLab's
notes API.

## Known limitation

Skill selection uses simple file-extension/keyword heuristics (see
`conditionalSkills()` in `review.js`), not the full nuance of an interactive
agent deciding what's relevant. Tighten the heuristics if you see obviously
wrong skills loading (or missing) for your stack.
