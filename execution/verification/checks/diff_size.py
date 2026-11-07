"""Diff-size check (F68, DEC-020): a pushed branch may not exceed the atomic-changes line limit.

The functions decide from text, and run.py reads git. A base that cannot be resolved is an error and
never a skip (DEC-015, point 3).
"""

import re

DEFAULT_MAX_DIFF_LINES = 400
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


def measure(new_sha, base, *, run_git):
    """Meaningful changed lines between the merge-base of `base` and `new_sha`, and `new_sha`. A delete is 0."""
    if not new_sha or set(new_sha) <= {"0"}:
        return 0
    merge_base = run_git(["merge-base", base, new_sha]).strip()
    if not merge_base or any(char.isspace() for char in merge_base):
        raise DiffSizeError(f"could not resolve the merge-base of {base} and {new_sha[:8]}: {merge_base!r}")
    return count_meaningful_lines(run_git([*_DIFF_ARGS, merge_base, new_sha, "--"]))


def find_violations(measurements, max_lines):
    """measurements: (branch, lines, base) tuples. A branch over the limit is a violation; the limit itself passes."""
    return [
        {
            "check": "diff_size",
            "reason": f"{branch}: {lines} meaningful lines against {base} exceed the atomic-changes limit "
            f"of {max_lines} lines",
        }
        for branch, lines, base in measurements
        if lines > max_lines
    ]
