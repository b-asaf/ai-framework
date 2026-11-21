#!/usr/bin/env python3
"""diff-size-check.py - measure the current branch against the changed-lines limit (DEC-025, S.6c).

Usage:
  python diff-size-check.py [--repo PATH]

The number comes from the push gate's own functions (execution/verification/checks/diff_size.py), so it is the
number the gate counts. The framework folder is looked for next to this file, then in the global git setting
aiFramework.root (written by `python setup.py`): the scripts folder of a tool config is a link, so the first
place may not be the framework.

Output, one "KEY: value" per line:
  STATUS: OK | OVER | ERROR
  LINES: <meaningful changed lines of HEAD against the base>
  LIMIT: <the limit that applies: maxDiffLines, or the largest approved number when that is larger>
  CONFIGURED: <maxDiffLines>
  APPROVED: <largest Diff-Size-Approved number on the branch>      (only when there is one)
  BASE: <the ref the branch is measured against>
  REASON: <why>                                                    (only when not OK)

Exit code: 0 OK, 1 OVER, 2 ERROR. Staged changes are an ERROR: the approval commit would take them along.
A malformed approval line is an ERROR too, as it blocks the push.
"""

import argparse
import subprocess
import sys
from pathlib import Path

CHECK = Path("execution") / "verification" / "checks" / "diff_size.py"
ORDER = ("STATUS", "LINES", "LIMIT", "CONFIGURED", "APPROVED", "BASE", "REASON")


class CheckError(Exception):
    """The branch cannot be measured."""


def root_from_git_setting():
    try:
        result = subprocess.run(
            ["git", "config", "--global", "--get", "aiFramework.root"],
            capture_output=True, encoding="utf-8", errors="replace", stdin=subprocess.DEVNULL,
        )
    except OSError:
        return None
    value = result.stdout.strip()
    return Path(value) if result.returncode == 0 and value else None


def find_framework_root():
    beside = Path(__file__).resolve().parent.parent
    for candidate in (beside, root_from_git_setting()):
        if candidate is not None and (candidate / CHECK).is_file():
            return candidate
    raise CheckError("the framework folder was not found; run `python setup.py`, which sets git aiFramework.root")


def measure_branch(repo):
    """(lines, limit, configured, approved, base) of HEAD, from the push gate's own functions."""
    sys.path.insert(0, str(find_framework_root()))
    from execution.verification import run as gate
    from execution.verification.checks import diff_size
    from execution.verification.git_runner import run_git

    def git(args):
        return run_git(args, cwd=str(repo), error=diff_size.DiffSizeError)

    config, problem = gate._read_config(repo)
    if problem:
        raise CheckError(problem["reason"])
    try:
        if git(["diff", "--cached", "--name-only"]).strip():
            raise CheckError("staged changes would go into the approval commit; commit or unstage them first")
        head = git(["rev-parse", "--verify", "HEAD"]).strip()
        configured = diff_size.read_max_lines(config)
        base = diff_size.read_base(config, run_git=git)
        lines = diff_size.measure(head, base, run_git=git)
        approved, problems = diff_size.read_approvals(head, base, run_git=git)
    except diff_size.DiffSizeError as error:
        raise CheckError(str(error)) from error
    if problems:
        raise CheckError("; ".join(problems))
    return lines, max(configured, approved), configured, approved, base


def run(repo):
    lines, limit, configured, approved, base = measure_branch(repo)
    out = {"LINES": str(lines), "LIMIT": str(limit), "CONFIGURED": str(configured), "BASE": base}
    if approved:
        out["APPROVED"] = str(approved)
    if lines > limit:
        out["STATUS"] = "OVER"
        out["REASON"] = f"{lines} meaningful lines against {base} exceed the limit of {limit}"
        return 1, out
    out["STATUS"] = "OK"
    return 0, out


def main(argv=None):
    parser = argparse.ArgumentParser(description="Measure the current branch against the changed-lines limit.")
    parser.add_argument("--repo", default=".")
    args = parser.parse_args(argv)
    try:
        code, out = run(Path(args.repo).resolve())
    except CheckError as error:
        code, out = 2, {"STATUS": "ERROR", "REASON": str(error)}
    for key in ORDER:
        if key in out:
            print(f"{key}: {out[key]}")
    return code


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
