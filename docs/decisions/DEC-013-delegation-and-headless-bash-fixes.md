# Decision: Fix subagent delegation, headless bash handling, and delegation discipline uncovered while smoke-testing `/task` and `/review`

> **Filename note:** originally saved as `DEC-013-model-catalog-drift.md`,
> which collided with `DEC-011`'s actual model-catalog-drift topic and
> didn't describe this DEC's content at all. Renamed to
> `DEC-013-delegation-and-headless-bash-fixes.md`. No content below
> changed as part of the rename.

**Date:** 2026-09-07 through 2026-09-12
**Status:** accepted (Findings A–E, G); F partially accepted (hard block
accepted, soft guidance alone confirmed insufficient); `/review` end-to-end
verdict still not reliably achieved — see "Not resolved this session"

## Context
Item 4 (smoke-test `/task` headlessly) and item 5 (real `/review` verdict)
from the DEC-011/012 handoff had never been exercised end-to-end. Running
both headlessly, then in multi-turn continuations, surfaced seven separate
defects, all independently capable of causing a headless run to hang
indefinitely with no error, or to silently skip or misreport work it was
explicitly instructed to do correctly:

- **Finding A** — three subagents unreachable via delegation (`mode:
  primary` instead of `mode: subagent`)
- **Finding B** — ad-hoc bash file-discovery calls hang headlessly
- **Finding C** — chained/piped bash commands hang headlessly even when
  every sub-command is individually allowed; recurred twice more after
  its first fix, inside different pipeline stages
- **Finding D** — the orchestrator can silently perform a subagent's
  designated work itself instead of delegating, if it has a matching
  skill loaded; soft instruction alone did not stop this, a hard `deny`
  on the specific tool did
- **Finding E** — a subagent's own permission block can be missing
  `allow` rules for tools it legitimately needs (`lizard`, `jscpd`), and
  separately, a new permission category (`external_directory`) can block
  access to files outside the working repo with the same headless-ask-hang
  behavior as `bash`
- **Finding F** — the orchestrator can spawn opencode's anonymous,
  unconfigured `general` subagent for ad-hoc work instead of a named
  framework subagent or doing the work itself; soft instruction alone did
  not stop this either — only a hard `deny` on the `task` permission
  (`"general": deny`) did
- **Finding G** — the orchestrator assumed a conventional base-branch name
  (`main`) that does not exist in this repo, received a git error, and
  misread it as "no changes to review," issuing a false PASS verdict on a
  branch that in fact had 48 changed files including real source-code
  logic changes

A documentation-drift issue (`commands/task.md`'s "Check 1/Check 2"
summary not matching `orchestrator.md`'s real Step 1–10 sequence) was also
found and fixed, since it actively misled the initial diagnosis of Finding A.

## Options considered

**Finding A** — `architect.md`, `plan-reviewer.md`, `product-manager.md`
had `mode: primary`.
- Loosen the fallback `general` subagent's permissions instead — rejected;
  leaves delegation silently mis-routed.
- Fix the three files' `mode:` field to `subagent` — **chosen**; confirmed
  via diff against a known-working subagent that nothing else needed to
  change.

**Finding B** — ad-hoc bash equivalents (`Test-Path`, `Get-ChildItem`)
used instead of built-in `glob`/`grep`/`read`.
- Widen the bash catch-all itself — rejected; defeats the permission
  system's purpose.
- Add specific `allow` rules for the observed commands, as a backstop —
  chosen, but insufficient alone.
- Add explicit guidance to prefer built-in tools — **chosen**, applied
  together with the backstop.

**Finding C** — chained/piped bash commands hang even when every
sub-command is individually allowed, because permission matching
evaluates the full command string as one unit.
- Allow-list common chained patterns — rejected; combinations are
  unbounded.
- Add explicit guidance to never chain, issue commands separately —
  chosen as the only fix that scales to an open-ended set of possible
  chains. **This guidance was added once, then the same failure mode
  recurred twice more later in the session** (once with `2>&1 | Select-Object
  -First 1`, once with `Get-ChildItem | Select-String | Select-Object`),
  each time inside a different, deeper pipeline stage than where it was
  first observed and fixed. No hard backstop exists for this finding, since
  chained combinations can't be enumerated the way B's could — this is an
  accepted, currently-unresolved limitation, not a decision to leave it
  broken; see "Not resolved this session."

**Finding D** — orchestrator performed `@code-reviewer`'s lint/scan work
itself instead of delegating, with no `task`-type tool call and no
self-reported reasoning.
- Remove the `static-code-analysis` skill from the orchestrator's own
  visibility — rejected; skills are discovered dynamically across
  `~/.claude/skills` and `~/.config/opencode/skills`, no clean way to scope
  a skill to one subagent's context without a larger mechanism change.
- Add guidance stating a loaded skill is not authorization to skip
  delegation — tried first, **confirmed insufficient on its own**: a later
  validation run showed the orchestrator still performing the work
  directly with the guidance already in place.
- Add a hard `deny` on the specific tools (`lizard *`, `jscpd *`) in the
  orchestrator's own permission block — **chosen as the effective fix**;
  validated to work: hitting the deny forced the orchestrator to
  recognize it could not do the work itself and route to `@code-reviewer`
  instead, confirmed via `agent=code-reviewer mode=subagent` appearing in
  its own session immediately after.

**Finding E** — `code-reviewer.md` itself lacked `allow` rules for
`lizard`/`jscpd`, and a separate `external_directory` permission category
blocked access to `D:\ai-framework\skills\linting-tools\references\*`.
- Broaden `code-reviewer.md`'s bash catch-all — rejected, same reasoning
  as Finding B.
- Add specific `allow` entries for the two tools, and a new
  `external_directory` block permitting the specific reference path —
  **chosen**.

**Finding F** — orchestrator spawned opencode's anonymous `general`
subagent for ad-hoc work, which has no bash permissions of its own
(confirmed: even the pre-approved `git-context.ps1` call hit `ask` inside
a `general` session).
- Add guidance to never spawn the generic subagent — tried first,
  **confirmed insufficient on its own**: it recurred in a later run with
  the guidance already in place.
- Add a hard `deny` on `task` permission for pattern `general` — **chosen**;
  validated in one clean run (zero `asking`, zero `agent=general`, 6 clean
  steps under `agent=orchestrator` only, reaching a text conclusion) but
  the fix was later found **missing from the live file** (see Consequences)
  and, once restored, a subsequent run showed the `deny` correctly firing
  on a second `general` attempt, but did not on its own guarantee actual
  delegation happened afterward (see Finding G's run and the note under
  "Not resolved this session").

**Finding G** — orchestrator assumed base branch `main`, which doesn't
exist in this repo, misread the resulting git error as an empty diff, and
issued a false PASS.
- Hard-code the correct base branch (`dev`) into `orchestrator.md` —
  rejected; not portable across other repos this framework might run
  against.
- Add guidance to verify the base branch exists (checking
  `project-overview`/`git branch -a` first) and to never treat a failed
  git command's error output as an empty diff — **chosen**; validated
  directly: the very next run correctly reasoned "No `main`/`master`
  exists here... target branch is `dev`" and confirmed the diff resolved
  before proceeding, matching the actual 48-file diff this session had
  independently confirmed by hand.

## Decision
Files changed:
- `agents/architect.md`, `agents/plan-reviewer.md`,
  `agents/product-manager.md` — `mode: primary` → `mode: subagent`.
- `agents/orchestrator.md` — five new instruction sections ("Tool
  preference — file discovery", "Bash commands — never chain", "Never
  perform a subagent's designated work yourself", "Never spawn opencode's
  generic subagent", base-branch verification guidance in the `/review`
  entry point); bash permission block extended with `Test-Path *`,
  `Get-ChildItem *`, `Get-Content *`, `Select-String *` (`allow`) and
  `lizard *`, `jscpd *` (`deny`); new `task:` permission block added with
  `"general": deny`.
- `agents/code-reviewer.md` — bash `allow` entries added for `lizard *`,
  `jscpd *`; new `external_directory` permission block added.
- `commands/task.md` — rewritten as a pointer to `orchestrator.md`'s real
  Step 1–10 sequence.
- Encoding corruption (`ג€”`/`ג†’`/`Γ`-prefixed sequences → proper em dash /
  arrow characters) corrected in `orchestrator.md`, `task.md`, and
  `code-reviewer.md` where found; **the same corruption pattern was
  observed recurring in freshly generated model text throughout the
  session, in outputs unrelated to any of the edited files** — its source
  is not fully identified (see "Not resolved this session").

## Reasoning
1. **Deterministic beats agent-judgment, confirmed twice over.** Findings
   D and F both initially received soft, instructional fixes, and both
   were independently confirmed insufficient by a subsequent validation
   run showing the exact original failure recurring with the guidance
   already in place. Both were only actually fixed once converted to a
   hard `deny` at the permission layer. This is now empirical, not
   theoretical, within this same investigation — worth treating as a
   standing principle for any future fix of this shape: prefer a
   permission-layer block over an instruction whenever the framework's
   permission system can express the constraint at all.
2. **Trade-off:** each `allow` addition (Findings B, E) is a deliberate,
   narrow widening of permission scope, accepted because the alternative
   is an unrecoverable, silent, indefinite hang. Each `deny` addition
   (Findings D, F) narrows what the *orchestrator* can do, forcing
   real delegation — this trades a small amount of orchestrator
   flexibility for correctness of the delegation chain.
3. **Cheaper alternatives were tried and rejected in practice, not just in
   theory**, for D and F specifically — the "cheaper" option (soft
   guidance) was actually attempted first in both cases and empirically
   failed before the more expensive, more targeted `deny` fix was applied.
4. **What's now visible/possible that wasn't before:** headless `/task`
   runs reliably reach real subagent delegation (validated end-to-end
   through Step 4's branch proposal). Headless `/review` runs now
   correctly identify the real base branch and the real diff, correctly
   block the orchestrator from doing `@code-reviewer`'s or the generic
   fallback's work itself, and correctly grant the `task` permission for
   real delegation — but **a granted `task` permission does not yet
   reliably result in an actual `Task` tool call being made**, a distinct
   and newer observation than any of A–G above, discovered in the final
   validation run of this session and not yet fixed (see below).

## Consequences
**Easier:** `/task` can be trusted end-to-end today. `/review` no longer
produces trivially wrong results from hangs or from a wrong assumed base
branch — the false-PASS failure mode (Finding G) specifically is fixed and
validated.

**Harder / still open — stated plainly rather than glossed over:**
- **A live edit was lost mid-session.** The `task: {"general": deny}` block
  was added, validated working in one clean run, and was later found
  completely absent from the live file with no other change nearby —
  almost certainly an earlier, stale Notepad window overwriting a newer
  save. It was restored and re-verified, but this is a process risk, not
  a framework bug: manual multi-window editing of the same file during a
  long session is fragile. Recommend closing editor windows immediately
  after each save is verified, rather than leaving several open across a
  long session.
- **A granted `task` permission is not proof that delegation occurred.**
  In the final run of this session, `permission=task pattern=code-reviewer
  action=allow` was logged, but no `@code-reviewer` subagent session was
  ever created (confirmed: only one session ID exists in that run's
  entire debug log) — the orchestrator instead ran a chained bash search
  for the literal string "code-reviewer" and hit Finding C's hang before
  ever calling `Task`. This is a new, more subtle variant of Finding D:
  the model can apparently pause to "check on" a subagent before actually
  invoking it, and get sidetracked into other work in between. **Not
  fixed this session.**
- **Finding C is recurring despite its fix.** It has now been observed
  three times: the original `git-context.ps1`-mimicking chain, a
  `2>&1 | Select-Object -First 1` pipe, and a `Get-ChildItem | Select-String
  | Select-Object` pipe — each in a different part of the pipeline, after
  the guidance was already in place. Unlike B, D, and F, there is no
  available hard-`deny` backstop for this one, since piped/chained
  commands aren't a finite enumerable set. This remains a real, live gap.
- **Item 5 (`/review` producing a genuine, trustworthy PASS/FAIL verdict
  on real content) is still not achieved.** Finding G's fix is validated
  and correct as far as it goes (correct base branch, correct diff, no
  false pass), but no run this session completed all the way through
  `@code-reviewer` → `@qa` → `@gatekeeper` to a real verdict. This item
  should be picked up fresh, not as a continuation of this session's many
  interrupted/continued runs.

**Needs updating alongside this change:**
- Item 6 (deterministic model validation script) should be extended to
  lint every file in `agents/` for correct `mode:` values, and now also to
  check that any `deny` fix that depends on forcing a reaction (D, F) is
  actually present in the live file, not just documented as fixed — the
  lost-edit incident above shows a fixed-and-forgotten config value can
  silently regress with no test catching it.
- Not addressed, flagged separately: `Γ`-prefixed encoding corruption
  appearing in freshly generated model text in files never touched by any
  edit this session — source not identified; item 8 (graphify CRLF
  regression) remains fully open and unrelated to this DEC; `lizard` is
  confirmed not installed on this machine at all, independent of the
  permission fix, so `static-code-analysis`'s complexity check will still
  fail on missing-tool grounds whenever it legitimately runs.

## Automated verification

Added once `validate_agents.py` (item 6) gained a generic `requires-deny`
check. Before this, the only protection against a fix like Finding D's or
F's silently reverting (as `task: {"general": deny}` demonstrably did,
once, within this same session) was a human re-reading the live file —
exactly the failure mode that caused the reversion to go unnoticed until
a headless run hung on it. These directives are consumed automatically by
`validate_agents.py`; re-running it after any future edit to
`orchestrator.md` will catch a silent reversion of either fix.

<!-- requires-deny: agent=orchestrator permission="task.general" -->
<!-- requires-deny: agent=orchestrator permission="bash.lizard *" -->
<!-- requires-deny: agent=orchestrator permission="bash.jscpd *" -->

Confirmed current as of this update: running `validate_agents.py` against
the live repo shows all three still correctly set to `deny` — these fixes
have not regressed again since landing.

## Update — 2026-09-18: Gap 1 partial validation + new external blocker found

Live testing against `real repo` produced two clean
instances of `permission=task pattern=code-reviewer action.action=allow`
immediately followed by correct subagent session creation
(`agent=code-reviewer`, correctly parented) and real work starting right
away — no investigation-before-delegating detour in either. This is
positive evidence for the Gap 1 guidance, though not yet the "multiple
independent clean runs" bar this DEC set for trusting it — both runs were
cut short by an unrelated blocker (below) before a full `/review` verdict
was reached.

**New blocker, confirmed external — not a config issue in this repo:**
once inside the `@code-reviewer` subagent session, its own
`permission.bash` allow rules (`"git diff *"`, the `git-context.ps1`
powershell allow, etc.) are not being respected — every bash command
falls to the `"*": ask` catch-all regardless of a matching allow rule.
Confirmed via a same-run, side-by-side comparison: the identical literal
command matched and was allowed for `orchestrator` (primary) and denied
to the `"*": ask` fallback for `code-reviewer` (subagent) later in the
same log. This matches a known upstream `opencode` bug
(anomalyco/opencode#26747, "fixed" by PR #27201, merged 2026-05-13), but
related, still-open issues (#28682, #31485, #49347 — the last reported
against v1.18.31, the current latest release) suggest the `"*": ask` +
subagent interaction remains fragile on Windows even post-fix. Framework
is currently on opencode v1.17.20.

**Status: left open.** Do not attempt further edits to any agent's
`permission.bash` block chasing this specific symptom — already
conclusively proven not to be a config issue. Recheck once opencode is
upgraded, or a newer issue directly matching this reproduction is found
upstream.


All diagnostic artifacts generated during this investigation
(`review-*.json`, `review-*.txt`, `repro-*.json`, `repro-*.txt`,
`task-mt*.json`, `task-mt*.txt`, `task-repro*.json`, `task-repro*.txt`) were
removed from a working directory at the end of this
session. Pre-existing untracked files in that directory (`docs/`,
`.ai-framework.json`, `_opencode.json`, `graphify-out/`, `iperf.exe`,
`webos-keystore.jks`, `.handoff-graalvm-native-build-2026-09-03.md`,
`CONTEXT.md`) were left untouched, as they predate this session and were
not created by it.