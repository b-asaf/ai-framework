"""Git access shared by the verification checks (Phase 3A, DEC-015).

The checks decide from plain data, and this is the one place that runs git for them. A check passes its
own error class, so its callers keep catching the type they know. Output is decoded as UTF-8 with
replacement characters: the locale codec of Windows raises on a commit message or a file name that is not
valid text, and a check that crashes decides nothing. Git gets an empty stdin, so it never reads the input
of the hook that called the check.
"""

import subprocess


class GitError(Exception):
    """git could not be run, or it exited with an error."""


def run_git(argv, cwd=None, *, error=GitError):
    """Run `git <argv>` and return its stdout. Raise `error` when git cannot start or exits non-zero."""
    try:
        result = subprocess.run(
            ["git", *argv],
            cwd=cwd,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            stdin=subprocess.DEVNULL,
            check=False,
        )
    except OSError as problem:
        raise error(f"failed to run git {argv}: {problem}") from problem
    if result.returncode != 0:
        raise error(f"git {argv} failed: {result.stderr}")
    return result.stdout
