# Decision: Fix subagent delegation fallback and headless bash-discovery hangs in `/task`

**Date:** 2026-09-07
**Status:** accepted

## Context
Item 4 from the DEC-011/012 handoff — smoke-test `/task` headlessly — had
never actually been run this session and was unverified. A full headless
run (`--command task`, then multi-turn `--continue --session ... --agent
orchestrator`) surfaced two separate, previously-undetected defects that
independently caused any real multi-step task to hang indefinitely with no
error and no timeout:

1. `agents/architect.md`, `agents/plan-reviewer.md`, and
   `agents/product-manager.md` were configured with `mode: primary` instead
   of `mode: subagent`, unlike every other implementation/review agent in
   the framework. This meant the orchestrator's `Task`-tool delegation
   couldn't bind to them as valid targets.
2. The model, doing investigative work mid-task, sometimes reached for raw
   bash commands (`Test-Path`, `Get-ChildItem`) instead of the framework's
   built-in `glob`/`grep`/`read` tools. Those bash calls fell through
   `orchestrator.md`'s `"*": ask` permission catch-all, which has no
   developer present to answer in headless mode.

A separate, lower-severity documentation-drift issue (`commands/task.md`'s
"Check 1/Check 2" summary not matching `orchestrator.md`'s real Step 1–10
sequence) was found and fixed along the way, since it actively misled the
initial diagnosis.

## Options considered

**For the subagent binding failure (Finding A):**
- Loosen the fallback `general` subagent's own permissions so an
  accidental fallback doesn't hang — rejected. Treats the symptom;
  delegation would still silently land on the wrong, unconfigured agent
  (no model, no scoped permissions) instead of the intended one.
- Fix the three files' `mode:` field to `subagent` — **chosen**. Addresses
  the actual defect directly; confirmed via diff against a known-working
  subagent (`code-reviewer.md`) that no other frontmatter field needed to
  change.

**For the headless bash hang (Finding B):**
- Widen the bash catch-all itself (`"*": ask` → `"*": allow`) — rejected.
  Defeats the purpose of having a permission system at all.
- Add specific `allow` rules for the observed safe read-only commands only
  — chosen as a backstop, not the primary fix, since it only ever covers
  commands already seen failing, not the next one the model might reach for.
- Add explicit guidance steering the model toward the built-in `glob`/
  `grep`/`read` tools instead of bash equivalents for file discovery —
  **chosen** as the primary fix, since it addresses the actual behavior
  causing the fallback rather than just widening the allow-list indefinitely.
- Both of the last two were applied together (guidance + backstop allow-list),
  rather than picking one, since guidance alone depends on the model
  reliably following it every time.

**For the `task.md`/`orchestrator.md` drift:**
- Duplicate orchestrator.md's full step list into task.md — rejected, this
  is exactly the duplication that caused the drift in the first place.
- Make task.md a thin pointer, declare orchestrator.md authoritative on any
  disagreement — **chosen**.

## Decision
Three files' frontmatter corrected: `agents/architect.md`,
`agents/plan-reviewer.md`, `agents/product-manager.md` — `mode: primary` →
`mode: subagent`.

`agents/orchestrator.md` updated: new "Tool preference — file discovery"
section added to the agent's instructions, plus four new `allow` entries
(`Test-Path *`, `Get-ChildItem *`, `Get-Content *`, `Select-String *`) added
to the bash permission block, correctly ordered last per DEC-012's
catch-all → deny → ask → allow last-match-wins rule.

`commands/task.md` rewritten as a pointer to `orchestrator.md`'s Step 1–10
sequence rather than a competing summary.

Encoding corruption (`ג€”`/`ג†’` → em dash / arrow) present in both
`orchestrator.md` and `task.md` was also corrected while editing these files.

This touches three existing agents (`architect`, `plan-reviewer`,
`product-manager`) and one existing orchestrating agent (`orchestrator`).
No new skill, agent, or hook was added.

## Reasoning
1. **Deterministic, not agent-judgment.** Both core fixes are deterministic
   config corrections — a frontmatter field value, and a permission list —
   not something requiring the model to reason its way around at runtime.
   The one agent-facing piece (the "Tool preference" guidance) is
   necessarily a soft instruction, since it's steering a model's tool
   choice; the allow-list backstop exists specifically because that soft
   instruction alone isn't deterministic enough to fully rely on.
2. **Trade-off:** the allow-list additions slightly widen what bash commands
   run without a human prompt. This is a real, deliberate trade against
   strict permission minimalism — accepted because the four commands added
   are read-only, and the alternative (leaving them on `ask`) produces
   silent, indefinite hangs in headless mode with no way to recover, which
   is a worse outcome than a slightly broader read-only allow-list.
3. **Cheaper alternative considered and rejected:** patching the `general`
   fallback's permissions instead of fixing the three `mode:` fields would
   have been a smaller diff, but it would leave delegation silently
   mis-routing to an unconfigured, wrong agent indefinitely — cheaper to
   write, more expensive to have live in the framework.
4. **What's now visible/possible that wasn't before:** a developer running
   `/task` headlessly can now expect the full Step 1 → Step 4 flow
   (Clarify → Design → Plan Review → PR breakdown → Branch proposal) to
   actually complete, with real subagent delegation to `@architect` and
   `@plan-reviewer` visible in the debug log (`agent=architect
   mode=subagent`, `agent=plan-reviewer mode=subagent`) instead of silently
   falling back to an anonymous `general` agent or hanging with no
   diagnostic signal beyond a frozen process.

## Consequences
**Easier:** headless `/task` runs can now be trusted to actually exercise
real subagent delegation rather than silently degrading; item 5 (real
`/review` verdict) is now more likely to succeed cleanly, since
`@code-reviewer`, `@qa`, and `@gatekeeper` are subagents too and may have
been vulnerable to the same Finding A pattern, previously undetected
because `/review` was only smoke-tested at the dispatch/permission layer,
never at real delegation depth.

**Harder / still open:** neither fix eliminates the underlying mechanism —
an unanswered headless `ask` still hangs forever with no timeout; this
reduces how often it's triggered, it doesn't make a future hang
self-diagnosing. That's a candidate for its own item (a hard timeout that
converts a silent hang into a loud, logged failure).

**Needs updating alongside this change:**
- Item 6 (deterministic model validation script) should be extended to also
  lint every file in `agents/` for correct `mode:` values against how it's
  actually invoked (subagent vs. primary vs. `--command` target), since this
  exact class of misconfiguration — a missing/wrong `mode`/`agent` field
  silently degrading to a generic built-in — now has two known instances
  (this one, and the earlier `--command` → `build`-fallback case already in
  the handoff) and no automated check catches either.
- Not addressed, flagged for separate investigation: path inconsistency in
  orchestrator.md's "Always load" section (`project-overview/sub/stack.md`
  vs. observed real paths without a `sub/` folder); `Γאפ`-style encoding
  corruption still appearing in freshly generated model text, suggesting a
  further source (agent-guidelines or another loaded skill) beyond the two
  files fixed here; item 8 (graphify CRLF regression) remains fully open —
  an edit was attempted this session but did not land, confirmed via `git
  diff`/`git log` showing `skills/graphify/SKILL.md` unchanged since its
  August 30 commit.