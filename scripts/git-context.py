#!/usr/bin/env python3
"""Read-only git context for agents: working-tree status and current branch.

Replaces scripts/git-context.ps1 (F25: $env:USERPROFILE does not expand in
the bash tool). The output sections match the old script.
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
    except OSError as exc:
        print("STATUS: ERROR")
        print("REASON: could not run git: " + str(exc))
        return 1
    print("--- status ---")
    print(status)
    print("--- branch ---")
    print(branch or "(detached HEAD)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
