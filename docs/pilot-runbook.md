# Running the framework on a plan step (pilot runbook)

Use this when the framework's own agents implement a step of `docs/transition-plan.md`. It is the method of the 3A pilots (evidence E13). Run every command in Git Bash.

## Rules

- Work only in the worktree `/d/ai-framework-new`. `/d/ai-framework` is live: its folders are linked into `~/.config/opencode`, so a change there changes every project.
- One worktree and one branch at a time. Check that the branch name is free first (`git branch --list <name>`).
- Never click "Allow always". Allow once and note which command asked.
- The agent never pushes. You push, after the checks in section 4 are green.
- Do not hand the agent steps that change `agents/`, `hooks/`, `commands/`, `skills/`, `scripts/`, `opencode.json`, `AGENTS.md` or `setup.py`. Those files are live; an agent editing its own rules is not a pilot.
- Good pilot steps add new files with tests. A small fix can use `/quick` (at most 3 files and 60 changed lines); a new check with tests needs `/task`.

## 1. Start

```bash
cd /d/ai-framework && pwd
git pull
git branch --show-current
if [ -z "$(git branch --list 'feat/NAME')" ]; then
  git worktree add ../ai-framework-new -b feat/NAME
else
  echo "STOP: branch already exists"
fi
cd /d/ai-framework-new && pwd
git branch --show-current
```

Then run `opencode` in `/d/ai-framework-new`, type `/task` (or `/quick`) and paste the prompt.

## 2. Prompt template

## 3. While it runs

- Expected prompts: `python tools/validate_framework.py` (repo specific, deliberately not allowed in the generic agents), and the test runner for `code-reviewer` (read-only by design; `python -m lizard` is allowed for it).
- Never pipe a command into tail, head or grep: each part of a chain is checked separately (F54), so the pipe asks for permission. Read the whole output instead.
- Any other command that asks is an agent mistake. Allow it once, note it, and tighten the prompt next time.
- Answer the clarifying questions of the first steps; "follow the plan" is usually enough.

## 4. Check, then push

```bash
cd /d/ai-framework-new && pwd
git branch --show-current
git status --short
BASE=$(git merge-base main HEAD)
git log --oneline $BASE..HEAD
git diff --name-only $BASE..HEAD
OUT=$(git diff --name-only $BASE..HEAD | grep -v -E '^(execution/verification/|tests/)')
if [ -z "$OUT" ]; then echo "only allowed paths"; else echo "OUTSIDE THE ALLOWED PATHS: $OUT"; fi
python tools/validate_framework.py > /tmp/vf.txt 2>&1
tail -1 /tmp/vf.txt
grep -q "All agent validation checks passed" /tmp/vf.txt; VF=$?
python -m unittest > /tmp/ut.txt 2>&1; UT=$?
tail -3 /tmp/ut.txt
LZ=$(python -m lizard -C 10 -w $(git diff --name-only $BASE..HEAD | grep '\.py$'))
echo "lizard warnings: ${LZ:-none}"
```

Read the diff before pushing (`git diff $BASE..HEAD`). Push only when the validator, the tests and lizard are green, the paths are allowed, and the tree is clean: `git push -u origin feat/NAME`.

## 5. Merge and clean up

Open the link the push prints, use the commit message as the title and merge with a merge commit. Close every window inside `/d/ai-framework-new` and stop OpenCode. Then:

```bash
cd /d/ai-framework && pwd
git pull
if git branch --merged main | grep -q 'feat/NAME'; then
  git worktree remove ../ai-framework-new
  git branch -d feat/NAME
else
  echo "STOP: not merged into main yet"
fi
git log --oneline -2
git worktree list
git status --short
```

## 6. Reviewer benchmark

Run these from `/d/ai-framework` on `main`.

| What | Command |
|---|---|
| List the cases | `python -B -m execution.runner.benchmark --list-cases` |
| Summarize saved results | `python -B -m execution.runner.benchmark --summarize execution/runner/runs/<folder>/results.jsonl` |
| One review of a project | `python -B -m execution.runner.cli --role code-reviewer --target <project> --diff <patch file>` |
| The checks | `python tools/validate_framework.py`, `python tools/generate_routing.py --check`, `python -m unittest` |

A full benchmark (replace NAME, MODEL1 and MODEL2; the baseline is always added; `--trial` is needed only for experimental models; `model@high` sets a reasoning effort):

```bash
cd /d/ai-framework && pwd
unset OPENCODE_CONFIG
unset OPENCODE_CONFIG_DIR
OUT=/d/ai-framework/execution/runner/runs/bench-NAME
LOG=/d/benchmark.log
: > "$LOG"
nohup python -u -B -m execution.runner.benchmark --trial --repeats 3 --timeout 600 \
  --models github-copilot/MODEL1,github-copilot/MODEL2 \
  --out "$(cygpath -m $OUT)" < /dev/null > "$LOG" 2>&1 &
tail -f "$LOG" | cut -c1-170
```

If it was interrupted or the machine slept, rerun the same command with `--resume` and the same `--out`: it keeps the good rows and repeats the rest. Results, `summary.txt` and the run records are in the `--out` folder (not versioned).

## 7. Known problems on this machine

- `nohup ... &` without `< /dev/null` makes every run fail with `EBADF` (F56).
- A sleeping machine makes runs look hung and ruins the timings (F55). Turn sleep off for long runs and use `--resume`.
- Do not use `kill` or `taskkill` on python while a benchmark runs: it stops the benchmark.
- Python on Windows does not see Git Bash's `/tmp`; pass paths through `cygpath -m`.
- Quotes, pipes, braces and `&` in `opencode run` arguments break on the Windows shim (F10); attach files instead.
- A pasted block that is too large, or has more than one heredoc, can stop at a `>` prompt: press Ctrl+C and send smaller blocks.
