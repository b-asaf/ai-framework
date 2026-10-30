"""Dependency-change-approval check (Phase 3A, plan step 3A.2, DEC-015 point 7).

Human approval for a dependency manifest change is made visible via a
commit trailer (`Dependency-Approved:` by default), not proven by code --
the check can only detect the trailer's presence, not validate that the
approval it represents was genuine (DEC-015 point 7).

Approval is OR-across-all-supplied-pushed-commit-messages: the trailer
needs to appear on at least one line of at least one commit in the
pushed range, not on every commit that happens to touch a manifest. This
is a deliberate choice per DEC-015 point 7 and KISS, not an oversight --
requiring the trailer on every touching commit would reject legitimate
multi-commit changes (e.g. a manifest edit followed by a lockfile
regeneration commit) for no safety benefit.

An unresolvable merge-base (e.g. in a shallow/fresh clone where the
protected ref is not present locally) fails closed via
DependencyChangeError -- this is deliberate, not a bug: the check cannot
safely assume "no dependency change" when it cannot compute the diff.

A missing/unfetched old_sha (e.g. after a force-push rewrote remote
history) likewise fails closed through ordinary git failure handling;
the resulting error message should mention that a `git fetch` may be
needed to resolve it.

A branch deletion (new_sha all-zero) has no commits to inspect and
short-circuits to an empty result with zero git calls; a protected
branch being deleted is caught separately by the branch_protection check.
"""

import fnmatch
import posixpath

from ..git_runner import run_git as _run_git


class DependencyChangeError(Exception):
    """A dependency manifest changed without a visible approval trailer, or the
    change range could not be determined."""


MANIFEST_NAMES = (
    # The files the agents ask about before editing (agents/backend.md and agents/api.md).
    "package.json",
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "pom.xml",
    "build.gradle*",
    "requirements*.txt",
    "pyproject.toml",
    "poetry.lock",
    "Pipfile",
    "Pipfile.lock",
)

_ZERO_SHA = "0000000000000000000000000000000000000000"


def run_git(argv, cwd=None):
    """git through the shared helper, raising this check's own error."""
    return _run_git(argv, cwd=cwd, error=DependencyChangeError)


def find_violations(changed_paths, commit_messages, trailer="Dependency-Approved:"):
    """Return a violation if a manifest changed without a visible approval trailer.

    Pure function: no filesystem/git access.
    """
    matched = [
        path
        for path in changed_paths
        if any(
            fnmatch.fnmatchcase(posixpath.basename(path), pattern)
            for pattern in MANIFEST_NAMES
        )
    ]
    if not matched:
        return []

    for message in commit_messages:
        for line in message.splitlines():
            if line.strip().startswith(trailer):
                return []

    return [
        {
            "reason": "dependency_change_without_approval",
            "manifests": sorted(matched),
        }
    ]


def _resolve_new_branch_range(new_sha, protected_branch, *, run_git):
    """Resolve the diff range for a new-branch push (old_sha all-zero).

    Requires a concrete (non-glob) protected_branch to compute a merge-base
    against. Raises DependencyChangeError if that is not possible, or if
    the merge-base lookup fails or returns something unresolvable.
    """
    if not protected_branch or "*" in protected_branch or "?" in protected_branch:
        raise DependencyChangeError(
            "cannot determine a base to diff a new branch against: "
            f"protected_branch={protected_branch!r} is missing or not a concrete ref"
        )

    try:
        output = run_git(["merge-base", new_sha, protected_branch])
    except DependencyChangeError:
        raise
    except Exception as error:
        raise DependencyChangeError(f"merge-base lookup failed: {error}") from error

    merge_base = output.strip()
    if not merge_base or any(char.isspace() for char in merge_base):
        raise DependencyChangeError(f"could not resolve merge-base: output={output!r}")

    return f"{merge_base}..{new_sha}"


def _read_commit_range(old_sha, new_sha, protected_branch=None, *, run_git=run_git):
    if not old_sha:
        raise DependencyChangeError("old_sha is missing or empty; cannot determine commit range")

    if old_sha != _ZERO_SHA:
        return f"{old_sha}..{new_sha}"

    return _resolve_new_branch_range(new_sha, protected_branch, run_git=run_git)


def read_changed_paths(old_sha, new_sha, protected_branch=None, *, run_git=run_git):
    """Return the list of changed paths in the pushed commit range.

    old_sha missing/unfetched (e.g. after a force-push) fails closed via
    ordinary git failure handling -- a `git fetch` may be needed.
    """
    if not new_sha:
        raise DependencyChangeError("new_sha is missing or empty; cannot determine commit range")
    if new_sha == _ZERO_SHA:
        return []

    range_spec = _read_commit_range(old_sha, new_sha, protected_branch, run_git=run_git)
    output = run_git(["diff", "--name-only", "--no-renames", "-z", range_spec, "--"])

    parts = output.split("\0")
    if parts and parts[-1] == "":
        parts = parts[:-1]
    return [path for path in parts if path]


def read_commit_messages(old_sha, new_sha, protected_branch=None, *, run_git=run_git):
    """Return the list of commit messages in the pushed commit range."""
    if not new_sha:
        raise DependencyChangeError("new_sha is missing or empty; cannot determine commit range")
    if new_sha == _ZERO_SHA:
        return []

    range_spec = _read_commit_range(old_sha, new_sha, protected_branch, run_git=run_git)
    output = run_git(["log", "--format=%B%x00", range_spec])

    # git adds a newline after each terminator, so the last piece is "\n", not "": it is not a message.
    parts = output.split("\0")
    if parts and not parts[-1].strip():
        parts = parts[:-1]
    return parts
