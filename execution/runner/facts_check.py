"""Pure checks of the facts of a write role's run (Phase 3B, plan step 3B.1; DEC-015 point 4).

The report says which test files the role wrote; two tree snapshots say what changed. cross_check
compares them. Whether a changed file is a test or a production file depends on the project's
test pattern and is scored in the qa benchmark, not here. workflow_level is the workflow level of
the run status (plan section 5.3) and build_verification builds the object for RunRecord.verification.
Nothing here touches the file system or starts a process.
"""


def _normal(name):
    text = str(name).replace("\\", "/")
    return text[2:] if text.startswith("./") else text


def cross_check(tests_written, changes):
    """One message per disagreement between the report's tests_written and the changed files."""
    reported = {_normal(item["file"]) for item in tests_written}
    present = set(changes.added) | set(changes.modified)
    problems = [f"tests_written lists {name}, which was not added or modified" for name in sorted(reported - present)]
    for kind, names in (("added", changes.added), ("modified", changes.modified), ("deleted", changes.deleted)):
        problems += [f"{name} was {kind} but is not in tests_written" for name in names if name not in reported]
    return problems


def workflow_level(tests, problems):
    """success only when the tests passed and the report matches the tree."""
    return "success" if tests.passed and not problems else "failure"


def build_verification(command, tests, changes, problems):
    """The object that goes under RunRecord.verification."""
    return {
        "tests": {
            "command": command,
            "exit_code": tests.exit_code,
            "timed_out": tests.timed_out,
            "total_lines": tests.total_lines,
            "tail": list(tests.tail),
            "note": tests.note,
        },
        "changed_files": {
            "added": list(changes.added),
            "modified": list(changes.modified),
            "deleted": list(changes.deleted),
        },
        "problems": list(problems),
    }
