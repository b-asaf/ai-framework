# Workflow Guide

> How to work with the agentic framework day-to-day. Read this before your first session.

---

## The mental model

Think of yourself as a **tech lead** and the agents as a **dev team**. You stay engaged at the right checkpoints — not micromanaging every line, but not disappearing after giving a requirement either. Too hands-off and agents drift. Too hands-on and you lose the value.

---

## Before your first task — first-run analysis

The orchestrator runs a full first-run analysis automatically when you open a new project. It will:

1. Detect whether this is a monolith or microservices — and ask you to confirm
2. Determine if each repo is new, partial, or mature
3. Detect the language, framework, and tools in every repo
4. Discover the conventions already in use
5. Flag any violations of Clean Code, SOLID, KISS, or YAGNI
6. Generate `docs/refactoring-plan.md` if issues are found
7. Update `opencode.json`, `project-overview`, and this guide with project-specific notes

**You will be asked two questions during first-run:**
- Confirm or correct the architecture topology (monolith / microservices)
- Confirm the detected stack and conventions are accurate

Do not start feature work until first-run is complete. If a refactoring plan was generated, review it before beginning.

> See `docs/session-summary.md` for current framework state.

---

## Start with a clear problem statement

The quality of output is directly proportional to the quality of your input.

❌ Too vague:
> "Fix the export bug"

✅ Specific and useful:
> "The CSV export button on the user list page does nothing when clicked. The backend endpoint `GET /api/users/export` exists and returns 200 in Postman. The issue is somewhere in the FE — either the click handler, the API client, or the response handling. It was working before PR #47 was merged last Tuesday."

The more context you give upfront, the fewer clarification rounds you need.

---

## Your four key checkpoints

These are the moments where your attention matters most. Don't rubber-stamp them.

### Checkpoint 1 — Spec (product-manager)

Read every acceptance criterion carefully:
- Push back if something is out of scope or missing
- Add anything the agent missed
- Confirm the "out of scope" section is explicit

5 minutes here saves 30 minutes of fixing wrong implementation later.

### Checkpoint 2 — Design (architect)

Actually evaluate the proposed solutions:
- Question trade-offs: "Why not option 2? What's the real downside?"
- The PR breakdown table is your contract — make sure it's atomic enough
- If solutions are proposed and grilled (see below), engage with the questions honestly

### Checkpoint 3 — Diff (before the gate)

Once code-reviewer and QA have both passed, read what the agents produced
before the gatekeeper's final check:
- Does it match the agreed spec?
- Is it one concern only (matches one row in the PR breakdown)?
- Are there any files changed that shouldn't be?
- Do test names describe real behavior?

If something looks wrong, route back to the relevant agent — don't fix it manually.

### Checkpoint 4 — Commit & draft PR/MR (automatic)

Once the gatekeeper reports all PASS, the orchestrator commits, then runs one
deterministic script (`scripts/open-draft-pr.py`, see the `pr-provider` skill)
that detects where the repo is hosted, pushes the branch, and opens the PR/MR
in draft mode — no approval wait (see AGENTS.md Check 4). Provider detection
and the API calls are code, not model judgment: GitLab opens the MR through
`git push` options, GitHub and Azure DevOps through their REST APIs.

```bash
git add .
git commit -m "fix(users): resolve CSV export click handler not firing"
python open-draft-pr.py --title "fix(users): resolve CSV export click handler not firing"
```

You'll get a notification with the draft PR/MR link once it's done (or, if
the provider isn't recognized or a required token/PAT isn't set, a note
telling you exactly what to open manually). Review the diff and commit
message there, and mark it ready-for-review yourself when you're happy with
it — that step stays manual.

---

## One PR at a time

The architect produces a PR breakdown table. Work through it sequentially — don't let agents start PR 2 while PR 1 is still in review.

```
PR 1 → implement → lint → review → test → gate → auto commit & push → auto draft PR → YOU review the PR
PR 2 → only after PR 1 is pushed
```

Small, focused PRs are the goal. A reviewer should be able to understand the full scope in under 15 minutes.

---

## How to handle agent mistakes

Agents will make mistakes. The right pattern:

| Mistake type | What to do |
|---|---|
| Wrong implementation | Tell the agent specifically what's wrong, route back through the flow |
| Scope creep in the diff | Tell the orchestrator to split the PR |
| Bad pattern choice | Reject at architect stage — don't let it reach implementation |
| Test doesn't cover a case | Tell `@qa` exactly which case is missing |
| Reviewer missed something | Tell `@code-reviewer` what it missed and re-run |

**Never silently fix agent mistakes yourself** — always route back so the full review cycle reruns.

---

## Keep sessions focused

**One session = one task.** Don't ask the orchestrator to handle two unrelated things in the same conversation. Context accumulates and agents start conflating decisions from different tasks.

If a second issue comes up mid-session, note it and start a fresh session for it.

---

## Maintain project-overview and docs/

After every 3-4 tasks, spend 2 minutes reviewing:
- `skills/project-overview/SKILL.md` — patterns and stack details still accurate?
- `docs/architecture.md` — reflects recent changes?

Agents update these, but they can drift. Stale context leads to bad agent decisions.

---

## What good looks like end-to-end

```
You: describe the broken export button clearly
    ↓
product-manager grills you on requirements → you answer → spec confirmed (2-3 min)
    ↓
architect grills you on the solution → you engage → PR breakdown agreed (5 min)
    ↓
orchestrator: "Created branch `fix/csv-export-click-handler`." (automatic)
    ↓
frontend implements → shows diff → you approve
code-reviewer lints/scans, finds one issue → frontend fixes → reruns → approved
qa writes 2 tests → both pass → gatekeeper: all gates PASS
    ↓
orchestrator commits, pushes, opens a draft PR automatically:
"Pushed and opened draft PR: fix(users): resolve CSV export click handler → <URL>"
You review the PR and mark it ready-for-review when you're happy with it.
Total: ~20 minutes. Clean, atomic, reviewable.
```

---

## Anti-patterns to avoid

| Anti-pattern | Why it hurts |
|---|---|
| Vague task descriptions | Long clarification loops or wrong implementations |
| Approving agent output without reading | You lose the value of supervised mode |
| Fixing agent mistakes manually | Skips the review cycle, breaks the pattern registry |
| Multiple unrelated tasks in one session | Agents conflate context across tasks |
| Skipping the PR breakdown approval | Large unfocused PRs, hard to review |
| Not reviewing `project-overview` periodically | Agents make decisions on stale context |
| Rubber-stamping the grill questions | The grill only works if you engage honestly |

---

## The grill sessions

Two moments in the flow involve structured interrogation:

**Requirements grill** (`product-manager`) — before the spec is written, the agent asks probing questions about the requirement one at a time, each with a recommended answer. Engage honestly. Don't skip questions.

**Solution grill** (`architect`) — before any code is written, the agent stress-tests the proposed solution against your codebase and constraints. This is where bad assumptions get caught cheapest.

See the `grill-me` skill for how this works.