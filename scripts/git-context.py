#!/usr/bin/env python3
"""Read-only git context for agents: working-tree status and current branch.

Replaces scripts/git-context.ps1 (F25: $env:USERPROFILE does not expand in
the bash tool). It prints the old script's sections plus an ahead section (F21):
how many commits this branch has that the base branch does not.
"""
import subprocess
import sys


def git(*args):
    proc = subprocess.run(
        ["git", *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return proc.returncode, (proc.stdout + proc.stderr).rstrip()


def base_branch_ref():
    """Return the ref of the base branch (origin/HEAD, main or master), or None when there is none."""
    names = []
    code, head = git("symbolic-ref", "--short", "refs/remotes/origin/HEAD")
    if code == 0 and head.startswith("origin/"):
        names.append(head[len("origin/"):])
    names += ["main", "master"]
    for name in names:
        for ref in ("refs/heads/" + name, "refs/remotes/origin/" + name):
            if git("rev-parse", "--verify", "--quiet", ref)[0] == 0:
                return ref
    return None


def ahead_of_base():
    """Lines for the ahead section: how many commits HEAD has that the base branch does not (F21)."""
    ref = base_branch_ref()
    if ref is None:
        return ["AHEAD_OF_BASE: unknown", "REASON: no main or master branch found"]
    code, count = git("rev-list", "--count", ref + "..HEAD")
    count = count.strip()
    if code != 0 or not count.isdigit():
        return ["AHEAD_OF_BASE: unknown", "REASON: could not compare HEAD with " + ref]
    lines = ["AHEAD_OF_BASE: " + count, "BASE: " + ref.split("/", 2)[2]]
    if int(count) > 0:
        _, log = git("log", "--format=%h %s", "--max-count=5", ref + "..HEAD")
        lines += ["COMMIT: " + subject for subject in log.splitlines() if subject.strip()]
    return lines


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    try:
        code, status = git("status")
        if code != 0:
            reason = status.splitlines()[0] if status else "no output"
            print("STATUS: ERROR")
            print("REASON: git status failed: " + reason)
            return 1
        _, branch = git("branch", "--show-current")
        ahead = ahead_of_base()
    except OSError as exc:
        print("STATUS: ERROR")
        print("REASON: could not run git: " + str(exc))
        return 1
    print("--- status ---")
    print(status)
    print("--- ahead ---")
    for line in ahead:
        print(line)
    print("--- branch ---")
    print(branch or "(detached HEAD)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
