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


def _review_lines(data):
    header = f"verdict: {data['verdict']} ({len(data['findings'])} findings)"
    return [header] + [_finding(finding) for finding in data["findings"]]


def _qa_lines(data):
    lines = [f"outcome: {data['outcome']} ({len(data['tests_written'])} test files)"]
    lines += [f"  {item['file']}: {item['count']} tests, {item['covers'][:120]}" for item in data["tests_written"]]
    lines += [f"  gap: {gap[:160]}" for gap in data["gaps"]]
    lines += [f"  production issue in {issue.get('file', 'unknown')}: {issue['message'][:160]}" for issue in data["production_issues"]]
    return lines


def _report_lines(data):
    return _review_lines(data) if "verdict" in data else _qa_lines(data)


def _verification_lines(data):
    tests = data["tests"]
    state = "timed out" if tests["timed_out"] else f"exit {tests['exit_code']}"
    lines = [f"tests: {tests['command']} -> {state}"]
    lines += [f"  problem: {problem}" for problem in data["problems"]]
    return lines


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
        lines += _report_lines(outcome.report)
    if built.get("verification"):
        lines += _verification_lines(built["verification"])
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
    ok = status["execution"] == "success" and status["artifact"] == "success"
    return 0 if ok and status.get("workflow") != "failure" else 1


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(errors="replace")
    sys.exit(main())
