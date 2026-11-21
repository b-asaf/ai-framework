"""Diff-size check (F68, DEC-020): a pushed branch may not exceed the atomic-changes line limit.

The functions decide from text, and run.py reads git. A base that cannot be resolved is an error and
never a skip (DEC-015, point 3).

A commit message line "Diff-Size-Approved: <lines> <reason>" raises the limit of that one branch to the
largest such number (DEC-025). A line that starts that way and is not in this form is a violation.
"""

import re

DEFAULT_MAX_DIFF_LINES = 400
APPROVAL_TRAILER = "Diff-Size-Approved:"
MAX_APPROVAL_DIGITS = 9
_DIFF_ARGS = ["diff", "-U0", "-w", "--ignore-blank-lines", "-M", "--no-color", "--no-ext-diff", "--no-textconv"]
_IMPORT_ONLY = re.compile(r"^\s*(import\s|export\s+.*\s+from\s|const\s+.*=\s*require\()")
NO_BASE = (
    "no base to measure the branch against: origin/HEAD is not set and diffBaseBranch is not set in "
    ".ai-framework.json. Fix: git remote set-head origin --auto, or set diffBaseBranch (for example origin/main)."
)


class DiffSizeError(Exception):
    """The size of a branch cannot be decided."""


def read_max_lines(config=None):
    """The limit from maxDiffLines (a positive whole number), or 400 when the key is absent."""
    if config is None:
        config = {}
    if not isinstance(config, dict):
        raise DiffSizeError(f"config must be a dict or None, got {type(config)!r}")
    if "maxDiffLines" not in config:
        return DEFAULT_MAX_DIFF_LINES
    value = config["maxDiffLines"]
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise DiffSizeError(
            "maxDiffLines in .ai-framework.json must be a positive whole number (remove the key to use 400)"
        )
    return value


def _resolve_configured(value, run_git):
    name = value.strip() if isinstance(value, str) else ""
    if not name or name.startswith("-"):
        raise DiffSizeError("diffBaseBranch in .ai-framework.json must be a branch name")
    try:
        run_git(["rev-parse", "--verify", "--quiet", name + "^{commit}"])
    except DiffSizeError as error:
        raise DiffSizeError(
            f"diffBaseBranch {name!r} in .ai-framework.json does not resolve to a commit; fix it or remove it"
        ) from error
    return name


def _resolve_origin_head(run_git):
    try:
        name = run_git(["symbolic-ref", "--short", "refs/remotes/origin/HEAD"]).strip()
    except DiffSizeError as error:
        raise DiffSizeError(NO_BASE) from error
    if not name.startswith("origin/") or name == "origin/" or any(char.isspace() for char in name):
        raise DiffSizeError(NO_BASE)
    return name


def read_base(config=None, *, run_git):
    """The ref a branch is measured against: diffBaseBranch if set, else origin/HEAD, else an error."""
    if config is None:
        config = {}
    if not isinstance(config, dict):
        raise DiffSizeError(f"config must be a dict or None, got {type(config)!r}")
    if "diffBaseBranch" in config:
        return _resolve_configured(config["diffBaseBranch"], run_git)
    return _resolve_origin_head(run_git)


def _is_meaningful(body):
    return bool(body.strip()) and not _IMPORT_ONLY.match(body)


def count_meaningful_lines(diff_text):
    """Count added and removed lines in `git diff -U0` output, without blank lines and import-only lines."""
    total, in_hunk = 0, False
    for line in diff_text.splitlines():
        if line.startswith("diff --git"):
            in_hunk = False
        elif line.startswith("@@"):
            in_hunk = True
        elif in_hunk and line[:1] in ("+", "-") and _is_meaningful(line[1:]):
            total += 1
    return total


def _merge_base(new_sha, base, run_git):
    merge_base = run_git(["merge-base", base, new_sha]).strip()
    if not merge_base or any(char.isspace() for char in merge_base):
        raise DiffSizeError(f"could not resolve the merge-base of {base} and {new_sha[:8]}: {merge_base!r}")
    return merge_base


def _approved_number(rest):
    """The number of a `<lines> <reason>` approval, or None when the line is malformed."""
    parts = rest.split(None, 1)
    if len(parts) != 2:
        return None
    number = parts[0]
    if not (number.isascii() and number.isdigit()) or len(number) > MAX_APPROVAL_DIGITS:
        return None
    return int(number) or None


def parse_approval_lines(message):
    """(numbers, bad lines) for the Diff-Size-Approved lines of one commit message (DEC-025).

    A line counts when, after trimming, it starts with the trailer. `Diff-Size-Approved: <lines> <reason>`
    needs a whole number of 1 or more and a reason; any other line that starts that way is a bad line.
    """
    numbers, bad = [], []
    for line in message.splitlines():
        text = line.strip()
        if not text.startswith(APPROVAL_TRAILER):
            continue
        number = _approved_number(text[len(APPROVAL_TRAILER):])
        if number is None:
            bad.append(text)
        else:
            numbers.append(number)
    return numbers, bad


def read_approvals(new_sha, base, *, run_git):
    """(largest approved number or 0, problems) from the commits between the merge-base and `new_sha`.

    The range is the one `measure` counts, the whole branch, so an approval made before an earlier push
    still counts. A problem names the commit and the malformed line.
    """
    if not new_sha or set(new_sha) <= {"0"}:
        return 0, []
    merge_base = _merge_base(new_sha, base, run_git)
    output = run_git(["log", "--format=%H%x00%B%x03", f"{merge_base}..{new_sha}"])
    largest, problems = 0, []
    for record in output.split("\x03"):
        sha, _, message = record.lstrip("\n").partition("\x00")
        if not sha.strip():
            continue
        numbers, bad = parse_approval_lines(message)
        largest = max([largest, *numbers])
        problems.extend(
            f"commit {sha.strip()[:8]}: malformed approval line {line!r} "
            f"(expected '{APPROVAL_TRAILER} <lines> <reason>': a whole number of 1 or more, then a reason)"
            for line in bad
        )
    return largest, problems


def measure(new_sha, base, *, run_git):
    """Meaningful changed lines between the merge-base of `base` and `new_sha`, and `new_sha`. A delete is 0."""
    if not new_sha or set(new_sha) <= {"0"}:
        return 0
    merge_base = _merge_base(new_sha, base, run_git)
    return count_meaningful_lines(run_git([*_DIFF_ARGS, merge_base, new_sha, "--"]))


def find_violations(measurements, max_lines, approved=None):
    """measurements: (branch, lines, base) tuples. A branch over its limit is a violation; the limit itself passes.

    approved maps a branch to the largest Diff-Size-Approved number on it (DEC-025): the limit of that branch
    is the larger of max_lines and that number.
    """
    approved = approved or {}
    found = []
    for branch, lines, base in measurements:
        raised = approved.get(branch, 0)
        limit = max(max_lines, raised)
        if lines <= limit:
            continue
        reason = (
            f"{branch}: {lines} meaningful lines against {base} exceed the atomic-changes limit "
            f"of {limit} lines"
        )
        if raised > max_lines:
            reason += f" (raised to {raised} by a Diff-Size-Approved line on this branch)"
        found.append({"check": "diff_size", "reason": reason})
    return found
