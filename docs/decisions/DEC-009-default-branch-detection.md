# Decision: Separate protected-branch detection from diff-base resolution; detect the real
# default branch via origin/HEAD; require explicit config or unambiguous reflog evidence
# for the diff base; filter non-meaningful diff noise

**Date:** 2026-08-20 (finalized; supersedes an earlier same-numbered draft)
**Status:** accepted; implementation still being smoke-tested against real repos

## Context
Testing `DEC-007`'s diff-size backstop on a real repo
surfaced two separate, more significant issues than the one being tested:

1. **Protected branch ≠ diff base.** The original hook conflated two different questions —
   "where may I not push directly?" and "what do I diff against?" — using one hardcoded
   `PROTECTED="main master develop"` list for both. Confirmed by direct evidence: this
   repo's actual default branch (`git symbolic-ref refs/remotes/origin/HEAD`) is
   `temp-dev`, not any of the hardcoded names, and it also has multiple simultaneously
   relevant branches (`dev`, `temp-dev`, release branches). A single hardcoded list, or even
   "pick the first match," cannot correctly answer both questions for a repo like this.
2. **Raw `git diff --shortstat` is noisy.** Counting every inserted/deleted line, including
   whitespace reformatting and import churn, can trigger false positives on changes that are
   small in real content but large in raw diff.

## Options considered — protected branches
- A: Bigger hardcoded name list — rejected: no fixed list can cover every real naming
     convention; `temp-dev` as this repo's literal default proves the point
- B: Require every project to configure protected branches explicitly — rejected as the
     sole mechanism: silently protects nothing if the config step is skipped
- C: Detect via `git symbolic-ref refs/remotes/origin/HEAD` (git's own authoritative
     pointer), with `main`/`master`/`develop` as a fallback baseline and an optional
     `protectedBranches` array in `.ai-framework.json` (supporting exact names and trailing
     `*` wildcard patterns) as an additive extension — chosen

## Options considered — diff base
- D: Reuse the (now separated) protected-branches list, picking the first local match —
     the original approach; rejected once separated from question 1, since a repo can have
     several protected branches at once and "first in list order" has no relationship to
     which one a given feature branch actually came from
- E: Pick whichever protected branch gives the *most recent* common ancestor (merge-base
     timing) — considered as an intermediate fix; rejected: a recent common ancestor is
     evidence about commit graph history, not proof of actual branch creation or intended
     PR target — it can produce a confident-looking but wrong answer with no indication of
     the uncertainty
- F: Ask an LLM to guess the intended base — rejected outright, same reasoning as every
     other deterministic-vs-agentic decision in this framework: this is answerable
     deterministically when it's answerable at all, so it should never be guessed
- G: Explicit `diffBaseBranch` in `.ai-framework.json` when configured (highest priority,
     including support for a CI/PR integration to write it before invoking the gate); else
     git reflog evidence for the current branch's creation, accepted **only when it
     identifies exactly one protected branch unambiguously**; else skip the check entirely
     with a specific message — chosen

## Decision: Options C + G, plus meaningful-diff filtering
Protected-branch detection and diff-base resolution are now two independent code paths in
`hooks/pre-push`, sharing only the underlying protected-branches list (Option C) as an
input where relevant.

**Diff-base resolution (`resolve_diff_base`)**, in priority order:
1. `.ai-framework.json`'s `diffBaseBranch`, if configured — checked against local and
   `origin/` refs; a configured-but-nonexistent value is a **hard error** (blocks the push),
   since a misconfiguration here is more likely a real mistake worth surfacing than
   something to silently ignore.
2. Git reflog evidence for the current branch's creation. Two matching strategies:
   - Text match: reflog literally names the source branch (`"checkout: moving from X to
     Y"`), the common case when branching with an explicit source argument.
   - **SHA-based ancestry match** (added during testing — see Consequences): when reflog
     instead records `"branch: Created from HEAD"` (the more common real-world case, when
     already standing on the source branch before creating the new one), the branch
     creation's *commit SHA* is resolved from reflog and checked via `git merge-base`
     against each protected branch's tip — whichever protected branch's history the
     creation SHA actually belongs to is the match. This handles the majority real-world
     workflow that the text-only match alone missed.
   - Accepted only if exactly one protected branch matches across both strategies combined;
     multiple or zero matches fall through to the skip case.
3. Neither is deterministic → the diff-size check is **skipped** with an explicit message
   naming both remediation paths (configure `diffBaseBranch`, or have CI/PR tooling supply
   it) — never a silent guess.

**Meaningful-diff filtering (`meaningful_diff_lines`)**: `git diff --find-renames
--unified=0` piped through a deterministic awk filter that excludes blank lines,
whitespace-only lines, import-only lines (JS/TS `import`, Python `from X import Y`, C#/Java
`using X;`), and pure renames (naturally excluded by having no +/- content lines). Anything
not explicitly recognized as noise still counts — the filter is conservative in the safe
direction for a blocking gate (errs toward counting, never toward under-counting).

## Reasoning
1. Agent or deterministic? The core discipline of this whole decision: several plausible
   "deterministic-looking" approaches (Option E especially) were rejected specifically
   because producing *an* answer reliably is not the same as producing the *correct* answer
   reliably — the honest deterministic behavior when correctness can't be guaranteed is to
   skip and say so, not to guess confidently.
2. Trade-off: real, worth stating plainly — git reflog only has evidence for branches
   created locally. A developer who clones a repo and checks out an already-existing remote
   feature branch has no local "created from X" history for it. In practice this means
   `diffBaseBranch` (ideally supplied by CI/PR tooling) is likely to be the *primary*
   working path for many collaborative workflows, not merely a fallback — this is expected,
   not a defect, but worth knowing rather than being surprised the reflog path "doesn't
   often fire" in a busy shared repo.
3. Cheaper alternative: Option E was cheaper to implement than Option G but was rejected for
   correctness, not cost, reasons.
4. Visibility gained: every skip and every block states specifically why and what to do
   about it — misconfiguration, ambiguity, and genuine oversized diffs are never conflated
   into one vague message.

## Consequences
- `.ai-framework.json` gains `protectedBranches` (array, supports `name` and `prefix/*`
  patterns) and `diffBaseBranch` (string) as optional keys.
- `skills/atomic-changes/SKILL.md` documents both, alongside the existing `maxDiffLines`.
- **Real bug found and fixed during smoke testing, not just confirmed working**: the
  original reflog matching (text-only) silently failed on the most common real branching
  workflow (`git checkout <source>` then `git checkout -b <new>`, which git logs as
  `"Created from HEAD"`, not the source branch's name). The SHA-based ancestry fallback was
  added specifically to close this gap. This was caught by testing against real repos with
  real branch history, not by design review — consistent with this framework's established
  pattern (`DEC-003`, `DEC-008`) of smoke tests surfacing real gaps design alone didn't.
- As of this writing, end-to-end confirmation on `real project` is still in progress —
  repeated propagation issues (edits to `ai-framework/hooks/pre-push` not reliably reaching
  the target repo's actual `.git/hooks/pre-push` without every step of `setup.py` → 
  `git-template` → `git init` being explicitly re-run and verified) have slowed final
  confirmation. This is an operational/testing-discipline issue, not a design flaw in the
  hook logic itself, but worth its own follow-up note on making that propagation chain more
  foolproof (e.g. a `setup.py --verify`-style check that diffs source vs. installed hook
  content directly, rather than relying on manual byte-size comparisons).
