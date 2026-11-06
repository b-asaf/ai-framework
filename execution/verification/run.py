"""Pre-push gate edge script (Phase 3A, plan step 3A.2, DEC-015, DEC-018).

This is the one place in the gate that touches git, the filesystem and the
environment. Everything it reads is handed as plain data to
`gates/pre_push.py`, which decides; this module only reads, catches each
check's own error as a violation (DEC-015: a check that cannot decide is a
violation, never a pass), and prints the result.

`main` takes argv, stdin text, the environment and a run_git callable as
plain parameters -- no direct sys.argv/sys.stdin/os.environ/subprocess call
inside it -- so tests can drive it with fakes. The `if __name__ ==
"__main__":` block at the bottom is the only place that touches the real
process state.

Designed to work both as `python -m execution.verification.run` and as
`python path/to/execution/verification/run.py` directly: the `__main__`
block inserts the framework root (two parents up from this file) onto
sys.path before importing anything under `execution`, since a direct
script invocation does not otherwise see the framework root as a package
root.
"""

import json
from pathlib import Path

CONFIG_NAME = ".ai-framework.json"

_HINTS = {
    "branch_protection": "This branch is protected; open a feature branch and push that instead.",
    "dependency_change": (
        "A dependency manifest changed without a visible approval trailer; "
        "add a `Dependency-Approved:` line to a commit message in this push."
    ),
    "quick_lane": (
        "A commit marked `Lane: quick` exceeds the quick-lane limits; "
        "split the change or use the regular lane instead."
    ),
    "config": f"Fix {CONFIG_NAME} so it parses as a JSON object, or remove it.",
    "coverage": "Set coverage.minChangedLines in .ai-framework.json to a whole number from 0 to 100, or remove it.",
    "diff_size": "Split the branch into smaller PRs. If the reason names diffBaseBranch or maxDiffLines, fix it in .ai-framework.json.",
}


def _read_config(repo):
    """Read .ai-framework.json from repo. Missing -> {}. Unparseable -> a violation."""
    config_path = Path(repo) / CONFIG_NAME
    if not config_path.is_file():
        return {}, None
    try:
        data = json.loads(config_path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as error:
        return {}, {
            "check": "config",
            "reason": f"{CONFIG_NAME} cannot be read: {error}",
        }
    if not isinstance(data, dict):
        return {}, {
            "check": "config",
            "reason": f"{CONFIG_NAME} must be a JSON object, got {type(data).__name__}",
        }
    return data, None


def _fail_closed(check, reason):
    return {"check": check, "reason": reason}


def _coverage_violation(config, coverage_config):
    """A coverage minimum that is present but invalid is a violation, never a silent default (DEC-015 point 3)."""
    try:
        coverage_config.read_minimum(config)
    except coverage_config.CoverageConfigError as error:
        return [_fail_closed("coverage", str(error))]
    return []


def _records_by_branch(stdin_text, push_input):
    """Map branch name -> PushRecord, for refs/heads/ records only."""
    records_by_branch = {}
    for record in push_input.parse_push_records(stdin_text):
        if record.remote_ref.startswith("refs/heads/"):
            branch = record.remote_ref[len("refs/heads/") :]
            records_by_branch[branch] = record
    return records_by_branch


def _first_concrete(branches):
    """The first protected branch that is a plain name, not a pattern: the base a new branch is compared with."""
    return next((name for name in branches if not any(char in name for char in "*?[")), None)


def _read_per_ref_checks(ctx):
    """Read dependency_change and quick_lane data for every pushed branch.

    Returns (per_ref_changed_paths, per_ref_commit_messages,
    per_ref_quick_lane_measurements, violations) -- a check's own error
    for one ref becomes a violation for that ref and does not stop the
    others (DEC-015: fail closed per decision, not per run).
    """
    per_ref_changed_paths, per_ref_commit_messages, per_ref_measurements = {}, {}, {}
    violations = []
    protected_branch_for_new = _first_concrete(ctx.protected_branches)

    for branch in ctx.pushed_branches:
        record = ctx.records_by_branch[branch]
        old_sha, new_sha = record.remote_sha, record.local_sha

        try:
            changed_paths = ctx.dependency_change.read_changed_paths(
                old_sha, new_sha, protected_branch_for_new, run_git=ctx.dc_run_git
            )
            commit_messages = ctx.dependency_change.read_commit_messages(
                old_sha, new_sha, protected_branch_for_new, run_git=ctx.dc_run_git
            )
        except ctx.dependency_change.DependencyChangeError as error:
            violations.append(_fail_closed("dependency_change", f"{branch}: {error}"))
        else:
            per_ref_changed_paths[branch] = changed_paths
            per_ref_commit_messages[branch] = commit_messages

        try:
            measurements = _read_quick_lane_measurements(
                ctx.quick_lane, ctx.dependency_change, old_sha, new_sha,
                protected_branch_for_new, ctx.dc_run_git, ctx.ql_run_git,
            )
        except (ctx.quick_lane.QuickLaneError, ctx.dependency_change.DependencyChangeError) as error:
            violations.append(_fail_closed("quick_lane", f"{branch}: {error}"))
        else:
            per_ref_measurements[branch] = measurements

    return per_ref_changed_paths, per_ref_commit_messages, per_ref_measurements, violations


class _Context:
    """Plain holder for the modules and run_git wrappers _read_per_ref_checks needs."""

    def __init__(self, pushed_branches, protected_branches, records_by_branch,
                 dependency_change, quick_lane, dc_run_git, ql_run_git):
        self.pushed_branches = pushed_branches
        self.protected_branches = protected_branches
        self.records_by_branch = records_by_branch
        self.dependency_change = dependency_change
        self.quick_lane = quick_lane
        self.dc_run_git = dc_run_git
        self.ql_run_git = ql_run_git


def main(argv, stdin_text, env, run_git):
    from execution.verification import push_input
    from execution.verification.checks import branch_protection, coverage_config, dependency_change, quick_lane
    from execution.verification.gates import pre_push

    repo = argv[1] if len(argv) > 1 else "."
    skip_verification = str(env.get("SKIP_VERIFICATION", "")) == "1"
    if skip_verification:
        print(
            "SKIP_VERIFICATION=1: skipping dependency_change and quick_lane checks "
            "(branch_protection still runs)."
        )

    config, config_violation = _read_config(repo)
    violations = [config_violation] if config_violation else []
    violations.extend(_coverage_violation(config, coverage_config))

    def bp_run_git(args):
        return run_git(args, cwd=repo, error=branch_protection.BranchProtectionError)

    def dc_run_git(args):
        return run_git(args, cwd=repo, error=dependency_change.DependencyChangeError)

    def ql_run_git(args):
        return run_git(args, cwd=repo, error=quick_lane.QuickLaneError)

    try:
        pushed_branches = branch_protection.read_pushed_branches(stdin_text)
    except branch_protection.BranchProtectionError as error:
        violations.append(_fail_closed("branch_protection", str(error)))
        if not skip_verification:
            violations.append(_fail_closed("dependency_change", str(error)))
            violations.append(_fail_closed("quick_lane", str(error)))
        return _report(violations)

    try:
        protected_branches = branch_protection.read_protected_branches(config, run_git=bp_run_git)
    except branch_protection.BranchProtectionError as error:
        violations.append(_fail_closed("branch_protection", str(error)))
        protected_branches = []

    per_ref_changed_paths, per_ref_commit_messages, per_ref_measurements = {}, {}, {}
    if not skip_verification:
        ctx = _Context(
            pushed_branches, protected_branches, _records_by_branch(stdin_text, push_input),
            dependency_change, quick_lane, dc_run_git, ql_run_git,
        )
        per_ref_changed_paths, per_ref_commit_messages, per_ref_measurements, per_ref_violations = (
            _read_per_ref_checks(ctx)
        )
        violations.extend(per_ref_violations)

        try:
            max_files, max_lines = quick_lane.read_limits(config)
        except quick_lane.QuickLaneError as error:
            violations.append(_fail_closed("quick_lane", str(error)))
            max_files, max_lines = quick_lane.DEFAULT_MAX_FILES, quick_lane.DEFAULT_MAX_LINES
    else:
        max_files, max_lines = quick_lane.DEFAULT_MAX_FILES, quick_lane.DEFAULT_MAX_LINES

    violations.extend(
        pre_push.find_violations(
            pushed_branches,
            protected_branches,
            per_ref_changed_paths,
            per_ref_commit_messages,
            per_ref_measurements,
            max_files,
            max_lines,
            skip_verification=skip_verification,
        )
    )
    violations.extend(_diff_size_violations(repo, config, stdin_text, env, run_git))

    return _report(violations)


def _measure_branches(records, base, run_git, diff_size):
    """(branch, lines, base) for every pushed branch, and a violation for each branch that cannot be measured."""
    measurements, violations = [], []
    for branch, record in records.items():
        try:
            lines = diff_size.measure(record.local_sha, base, run_git=run_git)
        except diff_size.DiffSizeError as error:
            violations.append(_fail_closed("diff_size", f"{branch}: {error}"))
        else:
            measurements.append((branch, lines, base))
    return measurements, violations


def _diff_size_violations(repo, config, stdin_text, env, run_git):
    """The diff-size check (F68, DEC-020). A base or a branch that cannot be measured is a violation, not a skip."""
    from execution.verification import push_input
    from execution.verification.checks import diff_size

    if str(env.get("SKIP_DIFF_SIZE_CHECK", "")) == "1":
        print("SKIP_DIFF_SIZE_CHECK=1: skipping the diff-size check.")
        return []

    def ds_run_git(args):
        return run_git(args, cwd=repo, error=diff_size.DiffSizeError)

    try:
        max_lines = diff_size.read_max_lines(config)
        records = _records_by_branch(stdin_text, push_input)
        if not records:
            return []
        base = diff_size.read_base(config, run_git=ds_run_git)
    except (diff_size.DiffSizeError, push_input.PushInputError) as error:
        return [_fail_closed("diff_size", str(error))]
    measurements, violations = _measure_branches(records, base, ds_run_git, diff_size)
    return violations + diff_size.find_violations(measurements, max_lines)


def main_or_block(argv, stdin_text, env, run_git):
    """main(), but an unexpected error is a readable block and never a bare traceback (fail closed, DEC-015)."""
    try:
        return main(argv, stdin_text, env, run_git)
    except Exception as error:
        print(f"BLOCKED gate: internal error: {type(error).__name__}: {error}")
        print("  Fix the cause above, or bypass the gate once with: git push --no-verify")
        return 1


def _read_quick_lane_measurements(
    quick_lane, dependency_change, old_sha, new_sha, protected_branch, dc_run_git, ql_run_git
):
    """Measure every quick-lane commit in the pushed range for one ref.

    Reuses dependency_change.commit_range to resolve the same range (and
    the same new-branch merge-base rule) the dependency_change check uses,
    so both checks agree on what was pushed.
    """
    if not new_sha or new_sha == dependency_change._ZERO_SHA:
        return []

    range_spec = dependency_change.commit_range(old_sha, new_sha, protected_branch, run_git=dc_run_git)
    commits = quick_lane.read_commits_in_range(range_spec, run_git=ql_run_git)
    quick_lane_commits = quick_lane.find_quick_lane_commits(commits)
    return [
        quick_lane.read_commit_measurement(sha, run_git=ql_run_git)
        for sha, _message in quick_lane_commits
    ]


def _describe(violation):
    """Build a readable reason string from a violation's own shape.

    A violation already carries "reason" (fail-closed violations built by
    this module) or "check" plus the check's own fields (the three
    composed checks, tagged by gates/pre_push.py).
    """
    if "branch" in violation:
        return f"push to protected branch '{violation['branch']}' (matches '{violation['matched_pattern']}')"
    where = f" (branch {violation['pushed_branch']})" if "pushed_branch" in violation else ""
    if "manifests" in violation:
        return f"dependency manifest changed without an approval trailer: {', '.join(violation['manifests'])}{where}"
    if "sha" in violation:
        return f"commit {violation['sha'][:8]} exceeds the quick-lane limits: {violation['details']}{where}"
    return violation["reason"]


def _report(violations):
    """Print `BLOCKED <check>: <reason>` and a fix-hint line per violation; return the exit code."""
    for violation in violations:
        check = violation["check"]
        print(f"BLOCKED {check}: {_describe(violation)}")
        print(f"  {_HINTS.get(check, 'Fix the issue above and push again.')}")
    return 1 if violations else 0


if __name__ == "__main__":
    import os
    import sys

    _FRAMEWORK_ROOT = Path(__file__).resolve().parents[2]
    if str(_FRAMEWORK_ROOT) not in sys.path:
        sys.path.insert(0, str(_FRAMEWORK_ROOT))

    from execution.verification.git_runner import run_git as _real_run_git

    sys.stdin.reconfigure(encoding="utf-8", errors="replace")
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main_or_block(sys.argv, sys.stdin.read(), os.environ, _real_run_git))
