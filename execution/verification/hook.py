"""Edge script of the git hooks (plan step S.7, DEC-027, DEC-015).

hooks/pre-commit, hooks/commit-msg and hooks/pre-push are one launcher that finds the framework folder and
a working Python and runs this script with its own name. Each hook is decided here, in Python, and a hook that
cannot decide blocks with a readable reason and never passes silently:
  pre-commit  does nothing: protecting a branch is the git host's job (DEC-029); it stays so installed launchers work
  commit-msg  blocks a message whose first line is not a conventional commit line
  pre-push    runs the push gate (run.py) and then build-verify with the commands of .ai-framework.json
main takes argv, stdin text, the environment and a run_git callable, so tests can drive it with fakes; the
block at the bottom is the only place that touches the real process state.
"""

import os
import re
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from execution.verification import build_verify, run as gate  # noqa: E402
from execution.verification.git_runner import GitError, run_git as real_run_git  # noqa: E402

HOOKS = ("pre-commit", "commit-msg", "pre-push")
SUBJECT = re.compile(
    r"(feat|fix|chore|refactor|docs|test|style|perf|ci|build|hotfix|release)(\(.+\))?: .{1,100}"
)


def _block(hook, headline, lines):
    bypass = "git push --no-verify" if hook == "pre-push" else "git commit --no-verify"
    print(f"\nBLOCKED {hook}: {headline}")
    for line in lines:
        print(f"  {line}")
    print(f"  Bypass once (reviewed exception only): {bypass}\n")
    return 1


def first_subject(text):
    """The first line that is not blank and not a # comment, or None."""
    for line in text.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            return line.rstrip()
    return None


def commit_msg(path):
    try:
        text = Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError as error:
        return _block("commit-msg", f"the commit message file cannot be read: {error}", [])
    subject = first_subject(text)
    if subject is not None and SUBJECT.fullmatch(subject):
        return 0
    return _block(
        "commit-msg",
        "the commit message does not follow the conventional commits format.",
        [
            "Format: <type>(<scope>): <description>",
            "Types: feat fix chore refactor docs test style perf ci build hotfix release",
            "Example: feat: add user export to CSV",
            f"Your first line: {subject if subject is not None else '(none)'}",
        ],
    )


def pre_commit(repo, run_git):
    """Nothing to check: protecting a branch is the git host's job (DEC-029).

    The hook stays so that launchers already installed in repositories keep working."""
    return 0


def _build_verify(repo, env):
    if str(env.get("SKIP_BUILD_VERIFY", "")) == "1":
        print("build-verify skipped (SKIP_BUILD_VERIFY=1)")
        return 0
    commands, problem = build_verify.read_commands(repo)
    if problem:
        headline, fixes = problem
        return _block("pre-push", headline, [*fixes, "Once only: SKIP_BUILD_VERIFY=1 git push"])
    print("\nRunning build-verify before push...")
    try:
        code = build_verify.run_stages(commands, repo)
    except build_verify.BuildVerifyError as error:
        return _block("pre-push", str(error), ["Once only: SKIP_BUILD_VERIFY=1 git push"])
    if code == 0:
        return 0
    print("\nERROR: build-verify failed - push blocked.")
    print("  Fix the failure above, or SKIP_BUILD_VERIFY=1 git push to override.\n")
    return 1


def pre_push(repo, stdin_text, env, run_git):
    code = gate.main_or_block(["run.py", repo], stdin_text, env, run_git)
    if code != 0:
        print("\nERROR: push gate failed - push blocked (see the lines above).")
        print("  Bypass once (reviewed exception only): git push --no-verify\n")
        return 1
    return _build_verify(repo, env)


def _repo_root(run_git, cwd):
    try:
        return run_git(["rev-parse", "--show-toplevel"], cwd=cwd).strip() or cwd
    except GitError:
        return cwd


def main(argv, stdin_text, env, run_git, cwd="."):
    hook = argv[1] if len(argv) > 1 else ""
    if hook == "commit-msg":
        return commit_msg(argv[2] if len(argv) > 2 else "")
    if hook not in HOOKS:
        print(f"BLOCKED hook: unknown hook {hook!r}; expected one of {', '.join(HOOKS)}")
        return 1
    repo = _repo_root(run_git, cwd)
    if hook == "pre-commit":
        return pre_commit(repo, run_git)
    return pre_push(repo, stdin_text, env, run_git)


def main_or_block(argv, stdin_text, env, run_git, cwd="."):
    """main(), but an unexpected error is a readable block and never a bare traceback (fail closed, DEC-015)."""
    try:
        return main(argv, stdin_text, env, run_git, cwd)
    except Exception as error:
        hook = argv[1] if len(argv) > 1 else "hook"
        print(f"BLOCKED {hook}: internal error: {type(error).__name__}: {error}")
        print("  Fix the cause above, or bypass once with: --no-verify")
        return 1


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    _text = ""
    if len(sys.argv) > 1 and sys.argv[1] == "pre-push":
        sys.stdin.reconfigure(encoding="utf-8", errors="replace")
        _text = sys.stdin.read()
    sys.exit(main_or_block(sys.argv, _text, os.environ, real_run_git))
