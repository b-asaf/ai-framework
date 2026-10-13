#!/usr/bin/env python3
"""quick-lane-check.py - measure a quick fix against the fast lane limits (DEC-018).

Usage:
  python quick-lane-check.py --start    # STATUS: OK only if the working tree is clean before the fix starts
  python quick-lane-check.py            # measure the uncommitted change against HEAD

Options: --repo PATH, --max-files N, --max-lines N

Output, one "KEY: value" per line:
  STATUS: OK | OVER | ERROR
  FILES: <number of changed files>
  LINES: <added + deleted lines, ignoring whitespace-only changes; new files count every line>
  LIMITS: files <n>, lines <n>
  RESTRICTED: <manifest, lockfile or .ai-framework.json paths that changed>   (only when present)
  REASON: <why>                                                              (only when not OK)

Exit code: 0 OK, 1 OVER, 2 ERROR. The change is over the limit when it touches more files OR more lines than
allowed, or touches a restricted path. Limits default to 3 files and 60 lines; .ai-framework.json may set
quickLane.maxFiles and quickLane.maxLines.
"""

import argparse
import fnmatch
import json
import subprocess
import sys
from pathlib import Path, PurePosixPath

DEFAULT_MAX_FILES = 3
DEFAULT_MAX_LINES = 60
RESTRICTED_PATTERNS = (
    "package.json", "package-lock.json", "yarn.lock", "pnpm-lock.yaml",
    "pom.xml", "build.gradle", "build.gradle.kts",
    "requirements*.txt", "pyproject.toml", "poetry.lock", "Pipfile", "Pipfile.lock",
    ".ai-framework.json",
)


class CheckError(Exception):
    """The change cannot be measured."""


def git(repo, *args):
    try:
        result = subprocess.run(
            ["git", "-C", str(repo), *args],
            capture_output=True, encoding="utf-8", errors="replace",
        )
    except OSError as error:
        raise CheckError(f"git could not run: {error}") from error
    if result.returncode != 0:
        raise CheckError(f"`git {' '.join(args)}` failed: {result.stderr.strip()[-200:]}")
    return result.stdout


def read_limits(repo, max_files, max_lines):
    config_path = Path(repo) / ".ai-framework.json"
    if config_path.is_file():
        try:
            config = json.loads(config_path.read_text(encoding="utf-8-sig"))
        except ValueError as error:
            raise CheckError(f".ai-framework.json cannot be read: {error}") from error
        quick = config.get("quickLane", {}) if isinstance(config, dict) else {}
        if not isinstance(quick, dict):
            raise CheckError("quickLane in .ai-framework.json must be an object")
        for key in ("maxFiles", "maxLines"):
            value = quick.get(key)
            if value is not None and (not isinstance(value, int) or isinstance(value, bool) or value < 1):
                raise CheckError(f"quickLane.{key} in .ai-framework.json must be a positive integer")
        if max_files is None:
            max_files = quick.get("maxFiles")
        if max_lines is None:
            max_lines = quick.get("maxLines")
    return (max_files or DEFAULT_MAX_FILES, max_lines or DEFAULT_MAX_LINES)


def count_lines(path):
    data = path.read_bytes()
    if b"\0" in data:
        return 0
    return data.count(b"\n") + (1 if data and not data.endswith(b"\n") else 0)


def measure(repo):
    """Return (files, lines) of the uncommitted change against HEAD, untracked files included."""
    git(repo, "rev-parse", "--verify", "HEAD")
    tracked = git(repo, "diff", "--numstat", "-z", "--no-renames", "-w", "--ignore-blank-lines", "HEAD")
    files, lines = {}, 0
    for record in filter(None, tracked.split("\0")):
        added, deleted, path = record.split("\t", 2)
        count = 0 if added == "-" else int(added) + int(deleted)
        files[path] = count
        lines += count
    untracked = git(repo, "ls-files", "--others", "--exclude-standard", "-z")
    for path in filter(None, untracked.split("\0")):
        count = count_lines(Path(repo) / path)
        files[path] = count
        lines += count
    return files, lines


def restricted(paths):
    found = []
    for path in sorted(paths):
        name = PurePosixPath(path).name
        if any(fnmatch.fnmatch(name, pattern) for pattern in RESTRICTED_PATTERNS):
            found.append(path)
    return found


def run(args):
    repo = Path(args.repo).resolve()
    git(repo, "rev-parse", "--is-inside-work-tree")
    max_files, max_lines = read_limits(repo, args.max_files, args.max_lines)
    limits = f"files {max_files}, lines {max_lines}"
    if args.start:
        dirty = git(repo, "status", "--porcelain").strip()
        if dirty:
            return 2, {"STATUS": "ERROR", "LIMITS": limits,
                       "REASON": "the working tree is not clean; commit or stash the existing changes first"}
        return 0, {"STATUS": "OK", "FILES": "0", "LINES": "0", "LIMITS": limits}
    files, lines = measure(repo)
    out = {"FILES": str(len(files)), "LINES": str(lines), "LIMITS": limits}
    reasons = []
    if len(files) > max_files:
        reasons.append(f"{len(files)} files changed (limit {max_files})")
    if lines > max_lines:
        reasons.append(f"{lines} lines changed (limit {max_lines})")
    touched = restricted(files)
    if touched:
        out["RESTRICTED"] = ", ".join(touched)
        reasons.append("a manifest, lockfile or .ai-framework.json changed")
    if reasons:
        out["STATUS"] = "OVER"
        out["REASON"] = "; ".join(reasons)
        return 1, out
    out["STATUS"] = "OK"
    return 0, out


def main(argv=None):
    parser = argparse.ArgumentParser(description="Measure a quick fix against the fast lane limits.")
    parser.add_argument("--repo", default=".")
    parser.add_argument("--start", action="store_true", help="check that the working tree is clean")
    parser.add_argument("--max-files", type=int)
    parser.add_argument("--max-lines", type=int)
    args = parser.parse_args(argv)
    try:
        code, out = run(args)
    except CheckError as error:
        code, out = 2, {"STATUS": "ERROR", "REASON": str(error)}
    order = ("STATUS", "FILES", "LINES", "LIMITS", "RESTRICTED", "REASON")
    for key in order:
        if key in out:
            print(f"{key}: {out[key]}")
    return code


if __name__ == "__main__":
    sys.exit(main())
