"""qa benchmark (Phase 3B, plan step 3B.1): the qa role on the cases of qa_cases.py with different models.

The first model is the baseline, the production model of the role; the others differ from it only in the
profile of a bench root. A run passes when it added at least one test file, the tests pass on the correct
project (measured by the runner), the same tests fail on the mutant (run here with the text in Outcome.files)
and no file outside the test pattern was added, modified or deleted. NEEDS_DEVELOPER is not a pass; it is
counted on its own. Every run is appended to results.jsonl as soon as it ends.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from . import benchmark, facts, qa_cases, record, resolve, run
from .cli import NOT_RUN, REPO_ROOT
from .tree import snapshot

ROLE = qa_cases.ROLE
MUTANT_TIMEOUT = 120
_from_record = benchmark._from_record


@dataclass(frozen=True)
class QaScore:
    valid: bool
    outcome: str | None
    wrote_tests: bool
    production_changed: tuple
    passes_on_correct: bool | None
    catches_mutant: bool | None

    @property
    def passed(self):
        return bool(
            self.valid and self.wrote_tests and not self.production_changed
            and self.passes_on_correct is True and self.catches_mutant is True
        )


def _verification(outcome):
    return (outcome.record.get("verification") if outcome else None) or {}


def _changed(outcome):
    return _verification(outcome).get("changed_files") or {}


def _test_files(outcome):
    """Name -> text of the test files the run added; a file whose text was not captured is left out."""
    files = (outcome.files if outcome else None) or {}
    added = _changed(outcome).get("added", [])
    return {name: files[name] for name in added if qa_cases.is_test_file(name) and files.get(name) is not None}


def _production_changed(outcome):
    changed = _changed(outcome)
    names = changed.get("added", []) + changed.get("modified", []) + changed.get("deleted", [])
    return tuple(sorted(name for name in names if not qa_cases.is_test_file(name)))


def _passes_on_correct(outcome):
    tests = _verification(outcome).get("tests")
    if not tests:
        return None
    return tests["exit_code"] == 0 and not tests["timed_out"]


def _environment():
    return {key: value for key, value in os.environ.items() if key.upper() != "PWD"}


def tests_catch_mutant(case, test_files, work, runner=subprocess.run, which=shutil.which, timeout=MUTANT_TIMEOUT):
    """True when the written tests fail on the mutant, False when they pass, None when they could not run."""
    if not test_files:
        return None
    root = qa_cases.build_project(case, Path(work) / "mutant", mutant=True, extra=test_files)
    try:
        argv = facts.resolve_argv(facts.command_argv(qa_cases.TEST_COMMAND), root, which)
    except facts.FactsError:
        return None
    result = facts.run_tests(argv, root, timeout=timeout, runner=runner, environ=_environment())
    return None if result.note else result.exit_code != 0


def score_run(outcome, caught):
    report = outcome.report if outcome else None
    return QaScore(
        valid=report is not None,
        outcome=report["outcome"] if report else None,
        wrote_tests=any(qa_cases.is_test_file(name) for name in _changed(outcome).get("added", [])),
        production_changed=_production_changed(outcome),
        passes_on_correct=_passes_on_correct(outcome),
        catches_mutant=caught,
    )


def make_row(model, case, repeat, outcome, error, violation, caught):
    score = score_run(outcome, caught)
    row = {
        "model": model,
        "case": case.id,
        "repeat": repeat,
        "ran": outcome is not None,
        "valid": score.valid,
        "outcome": score.outcome,
        "wrote_tests": score.wrote_tests,
        "production_changed": list(score.production_changed),
        "passes_on_correct": score.passes_on_correct,
        "catches_mutant": score.catches_mutant,
        "passed": score.passed,
        "violation": violation,
        "slept": bool(outcome and outcome.slept),
    }
    row.update(_from_record(outcome.record if outcome else None))
    message = row.pop("message")
    row["error"] = error or message
    return row


def run_one(root, case, model, repeat, work, runs_dir, review, timeout, runner=subprocess.run, which=shutil.which):
    """Build the project, run qa in it, check the written tests on the mutant, and score. A run that could not start is a row too."""
    work = Path(work)
    target = qa_cases.build_project(case, work / "target")
    diff = qa_cases.write_patch(case, work / "case.patch")
    before = snapshot(target)
    outcome, error = None, None
    try:
        outcome = review(root, target, ROLE, diff, timeout=timeout)
    except NOT_RUN as problem:
        error = str(problem)
    violation = snapshot(target) != before
    if outcome:
        record.append_record(outcome.record, runs_dir)
    caught = None
    if outcome and _passes_on_correct(outcome):
        caught = tests_catch_mutant(case, _test_files(outcome), work, runner, which)
    return make_row(model, case, repeat, outcome, error, violation, caught)


def _root(repo_root, directory, spec, trial):
    model, effort = benchmark.split_spec(spec)
    return benchmark.make_bench_root(repo_root, directory, model, effort, trial, role=ROLE)


def _append(path, row):
    with open(path, "a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(row, sort_keys=True) + "\n")


def _test_reasons(row):
    reasons = []
    if row["passes_on_correct"] is False:
        reasons.append("tests fail on the correct code")
    if row["catches_mutant"] is False:
        reasons.append("tests do not catch the mutant")
    elif row["wrote_tests"] and row["passes_on_correct"] and row["catches_mutant"] is None:
        reasons.append("the tests could not be run on the mutant")
    return reasons


def why_not(row):
    """The reasons a row did not pass, in plain words."""
    reasons = []
    if not row["valid"]:
        reasons.append("no valid report")
    elif not row["wrote_tests"]:
        reasons.append("no test file added")
    if row["production_changed"]:
        reasons.append("changed " + ", ".join(row["production_changed"]))
    return reasons + _test_reasons(row)


def describe_row(row):
    head = f"{row['model']} {row['case']} #{row['repeat']}:"
    if not row["ran"]:
        return f"{head} not run ({row['error']})"
    verdict = "PASS" if row["passed"] else "FAIL (" + "; ".join(why_not(row)) + ")"
    return f"{head} {verdict}, outcome {row['outcome'] or 'no report'}, cost {row['cost']}"


def run_qa_benchmark(
    repo_root, models, case_ids, repeats, out_dir, review=run.run_review, timeout=run.RUN_TIMEOUT, progress=print,
    trial_models=(), runner=subprocess.run, which=shutil.which,
):
    """Run every model on every case, repeats times. Returns the rows and writes results.jsonl under out_dir."""
    cases = [qa_cases.get_case(case_id) for case_id in case_ids]
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    base = Path(tempfile.mkdtemp(prefix="qa-bench-"))
    rows = []
    try:
        roots = {spec: _root(repo_root, base / f"root-{n}", spec, spec in trial_models) for n, spec in enumerate(models)}
        for repeat, case, model in benchmark.schedule(cases, models, repeats):
            work = Path(tempfile.mkdtemp(prefix="case-", dir=base))
            row = run_one(roots[model], case, model, repeat, work, out / "runs", review, timeout, runner, which)
            rows.append(row)
            _append(out / "results.jsonl", row)
            progress(describe_row(row))
    finally:
        shutil.rmtree(base, ignore_errors=True)
    return rows


def model_stats(rows):
    stats = {
        "runs": len(rows),
        "not_run": benchmark._count(rows, "ran", False),
        "valid": benchmark._count(rows, "valid"),
        "passed": benchmark._count(rows, "passed"),
        "missed": benchmark._count(rows, "catches_mutant", False),
        "production": sum(1 for row in rows if row["production_changed"]),
        "refused": benchmark._count(rows, "outcome", "NEEDS_DEVELOPER"),
    }
    stats.update(benchmark._timing(rows))
    return stats


def _model_line(model, item):
    mean = f"{item['mean_ms'] / 1000:.0f} s" if item["mean_ms"] is not None else "n/a"
    return (
        f"{model}: passed {item['passed']}/{item['runs']}, valid {item['valid']}, tests that missed the mutant {item['missed']}, "
        f"runs that changed production files {item['production']}, needs developer {item['refused']}, "
        f"not run {item['not_run']}, cost ${item['cost']:.3f}, mean {mean}"
    )


def render_summary(rows, baseline):
    by_model = {}
    for row in rows:
        by_model.setdefault(row["model"], []).append(row)
    cases = len({row["case"] for row in rows})
    lines = [
        f"qa benchmark: {len(rows)} runs, {len(by_model)} models, {cases} cases",
        f"Baseline: {baseline}",
        "Passed = a test file was added, the tests pass on the correct code and fail on the mutant, no production file changed.",
    ]
    slow = sum(1 for row in rows if benchmark.suspect(row))
    if slow:
        lines.append(f"{slow} run(s) hit the timeout or slept; they count as not passed, repeat them by hand")
    lines += [_model_line(model, model_stats(items)) for model, items in by_model.items()]
    return "\n".join(lines)


def build_parser():
    parser = argparse.ArgumentParser(prog="python -m execution.runner.qa_benchmark", description="Compare models on the qa cases.")
    parser.add_argument("--models", default="", help="comma separated model ids to compare with the baseline; model@effort sets a reasoning effort")
    parser.add_argument("--cases", default="", help="comma separated case ids (default: all)")
    parser.add_argument("--repeats", type=int, default=benchmark.DEFAULT_REPEATS, help="runs per model and case")
    parser.add_argument("--out", default="", help="folder for results.jsonl, summary.txt and the run records")
    parser.add_argument("--repo-root", default=str(REPO_ROOT), help="framework folder with the profile and the policy")
    parser.add_argument("--timeout", type=int, default=run.RUN_TIMEOUT, help="seconds before one run is stopped")
    parser.add_argument("--trial", action="store_true", help="count the --models as approved inside this benchmark only")
    parser.add_argument("--list-cases", action="store_true", help="list the cases and stop")
    return parser


def _split(text):
    return [part.strip() for part in text.split(",") if part.strip()]


def _default_out():
    return record.DEFAULT_RUNS_DIR / ("qabench-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))


def _run_from_args(args, review):
    unknown = [case_id for case_id in _split(args.cases) if case_id not in qa_cases.CASE_IDS]
    if unknown or args.repeats < 1:
        print(f"not run: {'unknown case(s) ' + ', '.join(unknown) if unknown else '--repeats must be at least 1'}", file=sys.stderr)
        return 2
    try:
        baseline = resolve.resolve(ROLE, args.repo_root).model
    except resolve.ResolveError as error:
        print(f"not run: {error}", file=sys.stderr)
        return 2
    models = list(dict.fromkeys([baseline] + _split(args.models)))
    case_ids = _split(args.cases) or list(qa_cases.CASE_IDS)
    out = Path(args.out) if args.out else _default_out()
    print(f"planned {len(models) * len(case_ids) * args.repeats} runs; results in {out.as_posix()}")
    trial = set(_split(args.models)) if args.trial else set()
    rows = run_qa_benchmark(
        args.repo_root, models, case_ids, args.repeats, out, review=review, timeout=args.timeout, trial_models=trial
    )
    text = render_summary(rows, baseline)
    (out / "summary.txt").write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


def main(argv=None, review=run.run_review):
    args = build_parser().parse_args(argv)
    if args.list_cases:
        print("\n".join(f"{case.id}: {case.summary}" for case in qa_cases.CASES))
        return 0
    return _run_from_args(args, review)


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(errors="replace")
    sys.exit(main())
