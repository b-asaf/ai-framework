"""The facts stage of a write role's run, joined (Phase 3B, plan step 3B.1; DEC-015 points 1, 3 and 4).

prepare reads the test command from the real target before the run, never from the copy the agent
works in, because a write role could edit .ai-framework.json there. run_facts is called after the agent
has stopped and its report is valid: it compares the files the run changed with the report (tree.py,
facts_check.py), runs the tests of the copy by code (facts.py) and returns the workflow level, the
object for RunRecord.verification and the error object. Only prepare and run_facts touch the file
system or start a process; the checks they call are pure.
"""

import shutil
import subprocess

from . import facts, facts_check, record, tree


def prepare(target):
    """(command, argv) of the target's test command; FactsError when it is missing or not plain."""
    command = facts.test_command(target)
    return command, facts.command_argv(command)


def _tests(argv, copy, timeout, runner, which, environ):
    try:
        resolved = facts.resolve_argv(argv, copy, which)
    except facts.FactsError as error:
        return facts.TestOutcome(-1, False, (), 0, str(error))
    return facts.run_tests(resolved, copy, timeout=timeout, runner=runner, environ=environ)


def _message(tests, problems):
    parts = list(problems)
    if tests.note:
        parts.append(tests.note)
    elif not tests.passed:
        parts.append(f"the tests failed with exit code {tests.exit_code}")
    return "; ".join(parts)


def run_facts(
    command, argv, copy, before, written, timeout=facts.TEST_TIMEOUT, runner=subprocess.run, which=shutil.which,
    environ=None,
):
    """(workflow level, verification object, error object or None) for a run that reached a valid report.

    The second snapshot is taken before the tests run, because a test run can write files of its own.
    """
    changes = tree.changed_files(before, tree.snapshot(copy))
    problems = facts_check.cross_check(written, changes)
    tests = _tests(argv, copy, timeout, runner, which, environ)
    level = facts_check.workflow_level(tests, problems)
    verification = facts_check.build_verification(command, tests, changes, problems)
    error = None if level == "success" else record.error_info(_message(tests, problems))
    return level, verification, error
