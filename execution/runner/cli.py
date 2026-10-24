"""Command line entry for one review run (Phase 2, plan step 2.1).

    python -m execution.runner.cli --role code-reviewer --target <project> --diff <file>

Runs the role's agent on the diff in the target project, appends the RunRecord
to execution/runner/runs/<date>.jsonl and prints a short summary. Exit code: 0
when the execution and artifact levels succeeded, 1 when a level failed (the
record says why), 2 when nothing ran (policy, preflight, a missing diff or
opencode).
"""

import argparse
import sys
from pathlib import Path

from . import opencode_adapter, preflight, record, resolve, run
from lib.opencode_resolved import ResolvedModelError  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
NOT_RUN = (resolve.ResolveError, preflight.PreflightError, opencode_adapter.AdapterError, ResolvedModelError)


def build_parser():
    parser = argparse.ArgumentParser(prog="python -m execution.runner.cli", description="Run one review through OpenCode.")
    parser.add_argument("--role", required=True, help="agent name, as in the profile")
    parser.add_argument("--target", required=True, help="project the agent runs in")
    parser.add_argument("--diff", required=True, help="file with the diff to review")
    parser.add_argument("--profile", default="default", help="profile name (default: default)")
    parser.add_argument("--repo-root", default=str(REPO_ROOT), help="framework folder with the profile and the policy")
    parser.add_argument("--timeout", type=int, default=run.RUN_TIMEOUT, help="seconds before OpenCode is stopped")
    return parser


def _finding(finding):
    where = finding.get("file", "(no file)")
    if "line" in finding:
        where += f":{finding['line']}"
    return f"  {finding['severity']} [{finding['category']}] {where}: {finding['message'][:160]}"


def _describe(outcome, path):
    built = outcome.record
    lines = [
        f"role {built['role']} on {built['resolved_model'] or 'no model reported'} (requested {built['requested_model']})",
        "status: " + ", ".join(f"{level} {value}" for level, value in built["status"].items()),
        f"cost {built['cost']} | {built['duration_ms']} ms | record {Path(path).as_posix()}",
    ]
    if built["error"]:
        lines.append("error: " + built["error"]["message"])
    if outcome.report:
        lines.append(f"verdict: {outcome.report['verdict']} ({len(outcome.report['findings'])} findings)")
        lines += [_finding(finding) for finding in outcome.report["findings"]]
    return "\n".join(lines)


def main(argv=None, review=run.run_review, runs_dir=None):
    args = build_parser().parse_args(argv)
    try:
        outcome = review(args.repo_root, args.target, args.role, args.diff, profile_name=args.profile, timeout=args.timeout)
    except NOT_RUN as error:
        print(f"not run: {error}", file=sys.stderr)
        return 2
    path = record.append_record(outcome.record, runs_dir)
    print(_describe(outcome, path))
    status = outcome.record["status"]
    return 0 if status["execution"] == "success" and status["artifact"] == "success" else 1


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(errors="replace")
    sys.exit(main())
