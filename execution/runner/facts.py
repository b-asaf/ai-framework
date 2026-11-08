"""The facts stage of a write role's run (Phase 3B, plan step 3B.1; DEC-015 points 1, 3 and 4).

After the agent stops, code states what happened instead of the agent: it runs the target's test
command itself. The command is the `test` key of .ai-framework.json, split into argv without a
shell, so shell syntax is rejected and never interpreted, and a missing or bad key fails closed.
command_argv is pure; test_command, resolve_argv and run_tests read files or start a process.
facts_check.py holds the pure checks of the facts, tree.py the file snapshots.
"""

import json
import re
import shlex
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

CONFIG_NAME = ".ai-framework.json"
TEST_TIMEOUT = 600
TAIL_LINES = 40
SHELL_SYNTAX = re.compile(r"[|&;<>`$(){}\\\r\n]")


class FactsError(Exception):
    """The facts stage cannot run, or cannot decide."""


@dataclass(frozen=True)
class TestOutcome:
    """What running the tests gave; the exit code is -1 when they did not run to an end."""

    exit_code: int
    timed_out: bool
    tail: tuple
    total_lines: int
    note: str | None = None

    @property
    def passed(self):
        return self.exit_code == 0 and not self.timed_out


def test_command(target):
    """The `test` command of the target's .ai-framework.json, or FactsError (fail closed)."""
    try:
        data = json.loads((Path(target) / CONFIG_NAME).read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as error:
        raise FactsError(f"{CONFIG_NAME} cannot be read: {error}") from error
    command = data.get("test") if isinstance(data, dict) else None
    if not isinstance(command, str) or not command.strip():
        raise FactsError(f"{CONFIG_NAME} has no test command, so the tests cannot be run (DEC-015)")
    return command.strip()


def command_argv(text):
    """Split a command into argv without a shell; shell syntax is rejected, not interpreted."""
    if not isinstance(text, str) or not text.strip():
        raise FactsError("the test command is empty")
    found = SHELL_SYNTAX.search(text)
    if found:
        raise FactsError(f"the test command {text!r} uses shell syntax ({found.group()!r}); give one plain command")
    try:
        return shlex.split(text)
    except ValueError as error:
        raise FactsError(f"the test command {text!r} cannot be split: {error}") from error


def resolve_argv(argv, cwd, which=shutil.which):
    """argv with its first item resolved to a file: a path against cwd, a name through PATH."""
    first = argv[0]
    if "/" in first:
        path = Path(cwd) / first
        found = str(path) if path.is_file() else None
    else:
        found = which(first)
    if found is None:
        raise FactsError(f"the test command {first!r} was not found")
    return [found] + list(argv[1:])


def _text(value):
    if value is None:
        return ""
    return value.decode("utf-8", "replace") if isinstance(value, bytes) else value


def run_tests(argv, cwd, timeout=TEST_TIMEOUT, runner=subprocess.run, environ=None):
    """Run the tests in cwd without a shell; a timeout or a failed start is a result, not an exception."""
    code, output, timed_out, note = -1, "", False, None
    try:
        done = runner(
            argv,
            cwd=str(cwd),
            env=environ,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
        code, output = done.returncode, _text(done.stdout)
    except subprocess.TimeoutExpired as error:
        timed_out, output = True, _text(error.stdout)
        note = f"the tests did not finish within {timeout} s"
    except OSError as error:
        note = f"the test command could not start: {error}"
    lines = output.splitlines()
    return TestOutcome(code, timed_out, tuple(lines[-TAIL_LINES:]), len(lines), note)
