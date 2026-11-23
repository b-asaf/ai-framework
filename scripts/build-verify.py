#!/usr/bin/env python3
"""build-verify.py - lint, format and test as a deterministic exit-code gate (DEC-027, plan step S.7).

Usage:
  python build-verify.py [--repo PATH] [--full] [--trim-lines N]
  python build-verify.py --lint "<cmd>" --format "<cmd>" --test "<cmd>" [--full] [--trim-lines N]

Without --lint, --format or --test it runs the lint, format and test commands of the repository's
.ai-framework.json, the file the pre-push hook reads. With any of them it runs only the stages named.
A failing stage prints the last lines of its output (--full prints all of it; the full log is always kept
in the git folder). The first failing stage stops the run.

Exit code: 0 all stages pass; 1 lint, 2 format or 3 test failed; 4 it cannot run (no .ai-framework.json or
no command in it, no shell, a bad flag). The code is in execution/verification/build_verify.py, found next
to this file or through the global git setting aiFramework.root (the scripts folder of a tool config is a link).
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

CANNOT_RUN = 4
CHECK = Path("execution") / "verification" / "build_verify.py"


class CheckError(Exception):
    """The framework folder was not found."""


class Parser(argparse.ArgumentParser):
    def error(self, message):
        print(f"build-verify: {message}", file=sys.stderr)
        sys.exit(CANNOT_RUN)


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


def default_trim():
    try:
        value = int(os.environ.get("BUILD_VERIFY_TRIM_LINES", ""))
    except ValueError:
        return 40
    return value if value > 0 else 40


def parse(argv):
    parser = Parser(description="Run lint, format and test as an exit-code gate.")
    parser.add_argument("--repo", default=".")
    parser.add_argument("--lint")
    parser.add_argument("--format")
    parser.add_argument("--test")
    parser.add_argument("--full", action="store_true")
    parser.add_argument("--trim-lines", type=int, default=default_trim())
    return parser.parse_args(argv)


def load_module():
    sys.path.insert(0, str(find_framework_root()))
    from execution.verification import build_verify

    return build_verify


def run(build_verify, args):
    repo = build_verify.repo_root(Path(args.repo).resolve())
    commands = {key: getattr(args, key) for key in ("lint", "format", "test") if getattr(args, key) is not None}
    if not commands:
        commands, problem = build_verify.read_commands(repo)
        if problem:
            print("\n".join([problem[0], *problem[1]]), file=sys.stderr)
            return CANNOT_RUN
    return build_verify.run_stages(commands, repo, full=args.full, trim_lines=args.trim_lines)


def main(argv=None):
    args = parse(argv)
    try:
        build_verify = load_module()
    except CheckError as error:
        print(str(error), file=sys.stderr)
        return CANNOT_RUN
    try:
        return run(build_verify, args)
    except build_verify.BuildVerifyError as error:
        print(str(error), file=sys.stderr)
        return CANNOT_RUN


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
