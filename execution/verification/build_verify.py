"""build-verify: lint, format and test as a deterministic exit-code gate (plan step S.7, DEC-027, DEC-015).

The commands are the lint, format and test keys of the project's .ai-framework.json. Each stage runs through
`sh -c` in the repository root and writes its output to a log file; only a failing stage prints its output (the
last lines by default). The first failing stage stops the run: exit code 1 for lint, 2 for format, 3 for test.
The callers are the pre-push hook (hook.py) and scripts/build-verify.py, which the implementation agents run.
"""

import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from .git_runner import GitError, run_git

CONFIG_NAME = ".ai-framework.json"
STAGES = (("LINT", "lint", 1), ("FORMAT", "format", 2), ("TEST", "test", 3))
CANNOT_RUN = 4
DEFAULT_TRIM_LINES = 40
_FIX_FILE = 'Fix: run the first-run analysis in an agent session, or create the file with a "test" command.'
_FIX_NOTHING = 'A repository with nothing to verify can set "test": "true".'
_FIX_COMMAND = 'Fix: add at least a "test" command; "test": "true" if there is nothing to run.'
_FIX_OBJECT = f"Fix: make {CONFIG_NAME} a JSON object."


class BuildVerifyError(Exception):
    """build-verify cannot run at all (no shell, or the shell could not start)."""


def _commands_from(data):
    commands = {}
    for _name, key, _code in STAGES:
        value = data.get(key)
        if value is not None and not isinstance(value, str):
            return None, (f"{key} in {CONFIG_NAME} must be a string", [f"Fix: make {key} one command, written as text."])
        commands[key] = (value or "").strip()
    if not any(commands.values()):
        return None, (f"{CONFIG_NAME} has no lint, format or test command.", [_FIX_COMMAND])
    return commands, None


def read_commands(repo):
    """(commands, None) with the stripped lint, format and test commands, or (None, (headline, fix lines))."""
    path = Path(repo) / CONFIG_NAME
    if not path.is_file():
        return None, (f"{CONFIG_NAME} not found: lint and tests cannot be verified.", [_FIX_FILE, _FIX_NOTHING])
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as error:
        return None, (f"{CONFIG_NAME} cannot be read: {error}", [_FIX_OBJECT])
    if not isinstance(data, dict):
        return None, (f"{CONFIG_NAME} must be a JSON object", [_FIX_OBJECT])
    return _commands_from(data)


def find_shell(which=shutil.which):
    """The `sh` the commands run through; on Windows the one that comes with Git for Windows."""
    found = which("sh")
    if found:
        return found
    git = which("git")
    if git:
        top = Path(git).resolve().parent.parent
        for relative in ("usr/bin/sh.exe", "bin/sh.exe"):
            if (top / relative).is_file():
                return str(top / relative)
    raise BuildVerifyError("no shell found: build-verify runs the project's commands through sh (on Windows it comes with Git for Windows)")


def repo_root(start):
    """The top folder of the repository that contains `start`, or `start` itself outside a repository."""
    try:
        return Path(run_git(["rev-parse", "--show-toplevel"], cwd=str(start)).strip() or start)
    except GitError:
        return Path(start)


def log_folder(repo):
    """Where the stage logs go: the git folder (also in a linked worktree), else the temp folder."""
    try:
        folder = Path(run_git(["rev-parse", "--absolute-git-dir"], cwd=str(repo)).strip()) / "build-verify-logs"
        folder.mkdir(parents=True, exist_ok=True)
    except (GitError, OSError):
        folder = Path(tempfile.gettempdir()) / "build-verify-logs"
        folder.mkdir(parents=True, exist_ok=True)
    return folder


def run_stage(command, repo, shell, log_file, run=subprocess.run):
    """Run one command through the shell with its output in log_file; return its exit code."""
    try:
        with open(log_file, "wb") as log:
            result = run(
                [shell, "-c", command], cwd=str(repo), stdout=log, stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL, check=False,
            )
    except OSError as error:
        raise BuildVerifyError(f"the shell {shell!r} could not run the command: {error}") from error
    return result.returncode


def show_failure(name, code, log_file, full, trim_lines, out):
    out(f"== {name}: FAIL (exit {code}) ==")
    text = Path(log_file).read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    if full or len(lines) <= trim_lines:
        out(text.rstrip("\n"))
        return
    out(f"-- showing last {trim_lines} of {len(lines)} lines (full log: {log_file}) --")
    out("\n".join(lines[-trim_lines:]))
    out(f"-- run with --full, or 'cat {log_file}', for everything --")


def run_stages(commands, repo, *, full=False, trim_lines=DEFAULT_TRIM_LINES, out=print, shell=None, run=subprocess.run):
    """Run lint, format and test in order and stop at the first failure.

    Returns 0 when every stage passes, else 1 (lint), 2 (format) or 3 (test). A stage without a command is skipped.
    """
    shell = shell or find_shell()
    folder = log_folder(repo)
    for name, key, failure_code in STAGES:
        command = commands.get(key, "")
        if not command:
            out(f"== {name}: SKIPPED (no command configured) ==")
            continue
        out(f"== {name}: running `{command}` ==")
        log_file = folder / f"{name.lower()}.log"
        code = run_stage(command, repo, shell, log_file, run)
        if code == 0:
            out(f"== {name}: PASS ==")
            continue
        show_failure(name, code, log_file, full, trim_lines, out)
        return failure_code
    out("== build-verify: ALL STAGES PASS ==")
    return 0
