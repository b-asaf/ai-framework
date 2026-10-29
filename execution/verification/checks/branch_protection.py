"""Branch-protection check (Phase 3A, plan step 3A.2, DEC-009, DEC-015, F14).

Protection is determined additively: the remote's `origin/HEAD` symbolic
ref (the repository-declared default branch) plus whatever entries are
configured under `protectedBranches`, never a hardcoded list (DEC-009).
Missing both sources is fail-closed (DEC-015): the check raises rather
than silently allowing every push through.

This replaces the behavior of today's `hooks/pre-push`, which warns and
skips the check whenever neither `origin/HEAD` nor a configured
`protectedBranches` list is available (F14) -- that gap meant a push to
a protected branch could slip through with only a warning. This check
blocks instead.

Empty stdin and tag-only push input both yield no branch names; that is
not an error, it simply means there is nothing for this check to inspect.
A branch deletion push (local sha all zeros) still names a branch on the
remote side and remains fully subject to protection.
"""

import fnmatch
import subprocess


class BranchProtectionError(Exception):
    """Branch protection could not be determined, or a protected branch was pushed to."""


def run_git(argv, cwd=None):
    try:
        result = subprocess.run(
            ["git", *argv], cwd=cwd, capture_output=True, text=True, check=False
        )
    except OSError as error:
        raise BranchProtectionError(f"failed to run git {argv}: {error}") from error
    if result.returncode != 0:
        raise BranchProtectionError(f"git {argv} failed: {result.stderr}")
    return result.stdout


def find_violations(pushed_branches, protected_branches):
    """Return one violation per pushed branch that matches a protected pattern.

    Pure function: no filesystem/git access. Matching uses fnmatch.fnmatchcase
    (case-sensitive) so each protected entry may be an exact name or a
    `prefix/*` style glob. When multiple protected entries match the same
    branch, only the first match (in protected_branches order) is reported.
    """
    violations = []
    for branch in pushed_branches:
        for pattern in protected_branches:
            if fnmatch.fnmatchcase(branch, pattern):
                violations.append(
                    {
                        "branch": branch,
                        "matched_pattern": pattern,
                        "reason": "protected_branch_push",
                    }
                )
                break
    return violations


def read_pushed_branches(stdin_text):
    """Parse pre-push stdin text (`local_ref local_sha remote_ref remote_sha` lines).

    Impure in the sense that it parses externally-sourced text, but it does
    not read sys.stdin itself -- the caller passes the text. Any malformed
    record raises BranchProtectionError (fail closed), even if other lines
    in the same input are well-formed.
    """
    if not stdin_text.strip():
        return []
    branches = []
    for line in stdin_text.splitlines():
        if not line.strip():
            raise BranchProtectionError(f"malformed pre-push input line: {line!r}")
        fields = line.split()
        if len(fields) != 4:
            raise BranchProtectionError(f"malformed pre-push input line: {line!r}")
        _local_ref, _local_sha, remote_ref, _remote_sha = fields
        if not remote_ref.startswith("refs/heads/"):
            continue
        branch = remote_ref[len("refs/heads/") :]
        if not branch:
            raise BranchProtectionError(f"empty branch name in remote_ref: {remote_ref!r}")
        branches.append(branch)
    return branches


def _validate_protected_branches_config(config):
    """Validate and normalize config, returning the validated protectedBranches list.

    Raises BranchProtectionError on any invalid shape (fail closed).
    """
    if config is None:
        config = {}
    if not isinstance(config, dict):
        raise BranchProtectionError(f"config must be a dict or None, got {type(config)!r}")

    configured = config.get("protectedBranches", [])
    if not isinstance(configured, list):
        raise BranchProtectionError(
            f"protectedBranches must be a list, got {type(configured)!r}"
        )
    validated_configured = []
    for entry in configured:
        if not isinstance(entry, str) or not entry.strip():
            raise BranchProtectionError(f"invalid protectedBranches entry: {entry!r}")
        validated_configured.append(entry.strip())
    return validated_configured


def _resolve_origin_branch(*, run_git):
    """Resolve origin/HEAD to a branch name, or return None if unavailable."""
    try:
        output = run_git(["symbolic-ref", "--short", "refs/remotes/origin/HEAD"])
    except Exception:
        return None

    stripped = output.strip()
    if not stripped.startswith("origin/"):
        return None
    remainder = stripped[len("origin/") :]
    if not remainder or any(char.isspace() for char in remainder):
        return None
    return remainder


def read_protected_branches(config=None, *, run_git=run_git):
    """Combine origin/HEAD with configured protectedBranches (DEC-009, additive).

    Fails closed: if neither source yields anything, raises
    BranchProtectionError naming both missing sources.
    """
    validated_configured = _validate_protected_branches_config(config)
    origin_branch = _resolve_origin_branch(run_git=run_git)

    combined = []
    if origin_branch is not None:
        combined.append(origin_branch)
    for entry in validated_configured:
        if entry not in combined:
            combined.append(entry)

    if not combined:
        raise BranchProtectionError(
            "no protected branches available: origin/HEAD is not set and "
            "no protectedBranches are configured"
        )
    return combined
