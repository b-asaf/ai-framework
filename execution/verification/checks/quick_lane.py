"""Quick-lane limit check (Phase 3A, plan step 3A.2, DEC-018, DEC-015).

DEC-018 lets the developer declare a quick fix (`Lane: quick` commit
trailer) that skips the spec grill and the HLD, but its limits (default
3 files / 60 changed lines, or any restricted manifest/lockfile/config
path) still apply, and `scripts/quick-lane-check.py` already enforces
them before the work is pushed. This check is the push-time backstop
DEC-018 calls for: a commit carrying the trailer that exceeds the limits
is blocked here even if the pre-work script was skipped or its limits
were since tightened in `.ai-framework.json`.

A "quick-lane commit" is identified by its own message, not by anything
in the branch name or in sibling commits: DEC-018 only ever puts the
trailer on the commit the developer's lane produced, so each commit is
judged on its own diff against its first parent (or against the empty
tree, for a root commit with no parent).

Limits come from `.ai-framework.json`'s `quickLane.maxFiles` /
`quickLane.maxLines`, mirroring `scripts/quick-lane-check.py`'s
`read_limits` validation exactly (DEC-018): a value present but not a
positive integer is a violation, not a silent fallback to the default
(DEC-015, fail closed).
"""


from ..git_runner import run_git as _run_git
from .dependency_change import MANIFEST_NAMES, is_manifest_path

LANE_TRAILER = "Lane: quick"
DEFAULT_MAX_FILES = 3
DEFAULT_MAX_LINES = 60
RESTRICTED_PATTERNS = MANIFEST_NAMES + (".ai-framework.json",)


class QuickLaneError(Exception):
    """A quick-lane commit could not be measured, or exceeds the lane limits."""


def run_git(argv, cwd=None):
    """git through the shared helper, raising this check's own error."""
    return _run_git(argv, cwd=cwd, error=QuickLaneError)


def is_quick_lane_message(message):
    """Return True if message carries the `Lane: quick` trailer line."""
    return any(line.strip().startswith(LANE_TRAILER) for line in message.splitlines())


def find_violations(measurements, restricted_patterns, max_files, max_lines):
    """Return one violation per quick-lane commit that is over the limits.

    Pure function: no filesystem/git access. measurements is an iterable of
    dicts with keys "sha", "files" (int), "lines" (int) and "paths" (an
    iterable of changed paths for that commit).
    """
    violations = []
    for measurement in measurements:
        reasons = []
        if measurement["files"] > max_files:
            reasons.append(f"{measurement['files']} files changed (limit {max_files})")
        if measurement["lines"] > max_lines:
            reasons.append(f"{measurement['lines']} lines changed (limit {max_lines})")
        restricted = [
            path
            for path in measurement["paths"]
            if is_manifest_path(path, restricted_patterns)
        ]
        if restricted:
            reasons.append("a manifest, lockfile or .ai-framework.json changed")
        if reasons:
            violations.append(
                {
                    "sha": measurement["sha"],
                    "reason": "quick_lane_over_limit",
                    "details": "; ".join(reasons),
                    "restricted": sorted(restricted),
                }
            )
    return violations


def _validate_positive_int(quick, key):
    value = quick.get(key)
    if value is not None and (not isinstance(value, int) or isinstance(value, bool) or value < 1):
        raise QuickLaneError(f"quickLane.{key} in .ai-framework.json must be a positive integer")
    return value


def read_limits(config=None):
    """Validate and return (max_files, max_lines) from config["quickLane"].

    Mirrors scripts/quick-lane-check.py's read_limits validation exactly:
    a present value that is not a positive integer is fail-closed via
    QuickLaneError, never silently replaced by the default.
    """
    if config is None:
        config = {}
    if not isinstance(config, dict):
        raise QuickLaneError(f"config must be a dict or None, got {type(config)!r}")

    quick = config.get("quickLane", {})
    if not isinstance(quick, dict):
        raise QuickLaneError("quickLane in .ai-framework.json must be an object")

    max_files = _validate_positive_int(quick, "maxFiles") or DEFAULT_MAX_FILES
    max_lines = _validate_positive_int(quick, "maxLines") or DEFAULT_MAX_LINES
    return (max_files, max_lines)


def find_quick_lane_commits(commits):
    """Return the (sha, message) pairs whose message carries the lane trailer.

    commits is an iterable of (sha, message) pairs for the pushed range, in
    any order; this function does not call git.
    """
    return [(sha, message) for sha, message in commits if is_quick_lane_message(message)]


def read_empty_tree(*, run_git=run_git):
    """Return the hash of the empty tree, obtained from git itself.

    Never hardcode the SHA1/SHA256 empty tree id: the object format of the
    repository decides which one is correct.
    """
    output = run_git(["hash-object", "-t", "tree", "--stdin"])
    empty_tree = output.strip()
    if not empty_tree or any(char.isspace() for char in empty_tree):
        raise QuickLaneError(f"could not resolve the empty tree: output={output!r}")
    return empty_tree


def _resolve_parent(sha, *, run_git):
    try:
        output = run_git(["rev-parse", f"{sha}^"])
    except QuickLaneError:
        return None
    parent = output.strip()
    if not parent or any(char.isspace() for char in parent):
        return None
    return parent


def read_commits_in_range(range_spec, *, run_git=run_git):
    """Return the (sha, message) pairs of every commit in range_spec.

    range_spec is a `old..new` (or similar) git revision range, already
    resolved by the caller (dependency_change.commit_range handles the
    new-branch merge-base case the same way for this check).
    """
    output = run_git(["log", "--format=%H%x00%B%x03", range_spec])
    records = output.split("\x03")
    if records and not records[-1].strip():
        records = records[:-1]
    commits = []
    for record in records:
        sha, _, message = record.lstrip("\n").partition("\x00")
        commits.append((sha, message))
    return commits


def read_commit_measurement(sha, *, run_git=run_git):
    """Measure one commit's own diff against its first parent.

    Returns a dict with keys "sha", "files", "lines" and "paths". Uses the
    empty tree (via read_empty_tree) when the commit has no parent, same as
    scripts/quick-lane-check.py's approach of diffing against a known base.
    """
    parent = _resolve_parent(sha, run_git=run_git)
    base = parent if parent is not None else read_empty_tree(run_git=run_git)

    output = run_git(
        ["diff", "--numstat", "-z", "--no-renames", "-w", "--ignore-blank-lines", base, sha]
    )
    paths = []
    lines = 0
    for record in filter(None, output.split("\0")):
        added, deleted, path = record.split("\t", 2)
        count = 0 if added == "-" else int(added) + int(deleted)
        lines += count
        paths.append(path)
    return {"sha": sha, "files": len(paths), "lines": lines, "paths": paths}
