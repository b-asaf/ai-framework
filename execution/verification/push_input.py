"""Shared parsing of pre-push stdin text (Phase 3A, plan step 3A.2, DEC-015).

The pre-push hook protocol feeds `local_ref local_sha remote_ref remote_sha`
lines on stdin, one per ref being pushed. Several checks need this same
information (`branch_protection` needs the `refs/heads/` branch names,
`dependency_change` and `quick_lane` need the shas to compute a commit
range), so the parsing lives here once and each check builds on top of it.

Any malformed record raises PushInputError (fail closed, DEC-015), even if
other lines in the same input are well-formed: a check that cannot decide
what was pushed must not silently decide nothing was.
"""

from collections import namedtuple

PushRecord = namedtuple("PushRecord", ["local_ref", "local_sha", "remote_ref", "remote_sha"])


class PushInputError(Exception):
    """The pre-push stdin text could not be parsed."""


def parse_push_records(stdin_text):
    """Parse pre-push stdin text into a list of PushRecord.

    Empty or whitespace-only input yields an empty list -- that is not an
    error, it simply means nothing was pushed. Any other malformed line
    (wrong field count, blank interior line) raises PushInputError.
    """
    if not stdin_text.strip():
        return []
    records = []
    for line in stdin_text.splitlines():
        if not line.strip():
            raise PushInputError(f"malformed pre-push input line: {line!r}")
        fields = line.split()
        if len(fields) != 4:
            raise PushInputError(f"malformed pre-push input line: {line!r}")
        records.append(PushRecord(*fields))
    return records
