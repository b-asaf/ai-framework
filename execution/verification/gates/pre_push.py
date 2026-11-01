"""Pre-push gate (Phase 3A, plan step 3A.2, DEC-015, DEC-018).

Composes three checks into the single decision `hooks/pre-push` needs:
branch_protection, dependency_change and quick_lane. protected_paths is
deliberately not part of this gate (it answers a different question --
whether a protected path changed during an agent run, section 5.6 -- not
whether a push should be blocked).

This module is pure: it takes plain data (already read by run.py at the
edge) and returns the combined list of violations. It never calls git or
touches the filesystem, so it is trivial to test with fabricated data.

SKIP_VERIFICATION, when set, skips dependency_change and quick_lane only
(DEC-018 still wants a visible record of what ran, so the caller is
responsible for printing the notice; this module only decides which
checks' violations are included). branch_protection is never skipped --
a protected branch must stay protected regardless of the environment.
"""

from ..checks import branch_protection, dependency_change, quick_lane


def find_violations(
    pushed_branches,
    protected_branches,
    per_ref_changed_paths,
    per_ref_commit_messages,
    per_ref_quick_lane_measurements,
    max_files,
    max_lines,
    *,
    skip_verification=False,
):
    """Return the combined violations from all three checks.

    per_ref_changed_paths, per_ref_commit_messages and
    per_ref_quick_lane_measurements are dicts keyed by branch name, each
    holding the data that ref's checks need (changed paths, commit
    messages, and quick-lane commit measurements respectively). max_files
    and max_lines are the already-resolved quick-lane limits (run.py reads
    and validates .ai-framework.json at the edge; this function only
    applies them).
    """
    violations = [
        dict(item, check="branch_protection")
        for item in branch_protection.find_violations(pushed_branches, protected_branches)
    ]

    if skip_verification:
        return violations

    for branch in pushed_branches:
        changed_paths = per_ref_changed_paths.get(branch, [])
        commit_messages = per_ref_commit_messages.get(branch, [])
        violations.extend(
            dict(item, check="dependency_change")
            for item in dependency_change.find_violations(changed_paths, commit_messages)
        )

    for branch in pushed_branches:
        measurements = per_ref_quick_lane_measurements.get(branch, [])
        violations.extend(
            dict(item, check="quick_lane")
            for item in quick_lane.find_violations(
                measurements, quick_lane.RESTRICTED_PATTERNS, max_files, max_lines
            )
        )

    return violations
