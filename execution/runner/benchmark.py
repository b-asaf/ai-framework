"""Reviewer benchmark (Phase 2, plan steps 2.3 and 2.5, decision #5).

Runs the real code-reviewer prompt on the cases of bench_cases.py with different
models, through the same run_review the command line uses, and scores what comes back
in code, not with another model. The first model is the baseline: the production model
of the role. The others differ from it only in the profile file: a bench root copies the
policy and the agent file, and only its profile names the model (the model swap
requirement of the gate).

Scoring is plain. A bug counts as found when a BLOCKING finding names the bug's file and
its text matches the case pattern. A clean diff is a false positive when the reply
blocks it. The line a finding cites is compared with the line in the file and with the
line in the patch (line_basis). A run that changes the target project is a permission
violation. Nothing here passes or fails a model: review_flags lists what a person should
look at, with a margin of one case worth of runs (decision #5).

Every run is appended to results.jsonl as soon as it ends, so an interrupted benchmark
keeps its results and --summarize can read them.
"""

import argparse
import hashlib
import json
import re
import shutil
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from . import bench_cases, record, resolve, run
from .cli import NOT_RUN, REPO_ROOT

ROLE = bench_cases.ROLE
DEFAULT_REPEATS = 3


def snapshot(directory):
    """Map of relative path to content hash for every file under directory except .git."""
    root = Path(directory)
    result = {}
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        if path.is_file() and not relative.startswith(".git/"):
            result[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def _write_policy(source, target, trial_model):
    """Copy the policy. For a trial the model counts as approved in the copy only; the repo policy is untouched."""
    if trial_model is None:
        shutil.copyfile(source, target)
        return
    data = json.loads(source.read_text(encoding="utf-8-sig"))
    entry = data.get("models", {}).get(trial_model)
    if isinstance(entry, dict):
        entry["status"] = "approved"
    target.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8", newline="\n")


def make_bench_root(repo_root, directory, model, effort=None, trial=False):
    """A framework folder that differs from repo_root only in the profile: the role runs on model."""
    source, root = Path(repo_root), Path(directory)
    (root / "execution" / "profiles").mkdir(parents=True)
    (root / "agents").mkdir()
    _write_policy(source / "execution" / "policy.json", root / "execution" / "policy.json", model if trial else None)
    shutil.copyfile(source / "agents" / f"{ROLE}.md", root / "agents" / f"{ROLE}.md")
    entry = {"model": model, "effort": effort} if effort else {"model": model}
    profile = {"version": 1, "agents": {ROLE: entry}}
    text = json.dumps(profile, indent=2) + "\n"
    (root / "execution" / "profiles" / "default.json").write_text(text, encoding="utf-8", newline="\n")
    return root


@dataclass(frozen=True)
class Score:
    valid: bool
    verdict: str | None
    blocking: int
    detected: bool | None
    line_basis: str | None
    false_positive: bool | None


def _same_file(reported, expected):
    return isinstance(reported, str) and reported in (expected, f"./{expected}", f"a/{expected}", f"b/{expected}")


def _blocking(report):
    if not report:
        return []
    return [finding for finding in report["findings"] if finding["severity"] == "BLOCKING"]


def _finding_hits(case, finding):
    text = f"{finding['category']} {finding['message']}"
    return _same_file(finding.get("file"), case.bug.file) and re.search(case.bug.pattern, text, re.I) is not None


def _line_basis(case, hits):
    file_line, patch_line = bench_cases.bug_lines(case)
    cited = {finding.get("line") for finding in hits}
    if file_line in cited:
        return "file"
    if patch_line in cited:
        return "patch"
    return None


def score_run(case, report):
    """Score one reply. A run without a valid report finds nothing and blocks nothing."""
    blocking = _blocking(report)
    verdict = report["verdict"] if report else None
    if case.bug is None:
        false_positive = bool(report) and (verdict == "REQUEST CHANGES" or bool(blocking))
        return Score(report is not None, verdict, len(blocking), None, None, false_positive)
    hits = [finding for finding in blocking if _finding_hits(case, finding)]
    basis = _line_basis(case, hits) if hits else None
    return Score(report is not None, verdict, len(blocking), bool(hits), basis, None)


def _from_record(built):
    if built is None:
        return {
            "status": None,
            "resolved_model": None,
            "fallback": False,
            "cost": None,
            "duration_ms": None,
            "run_id": None,
            "message": None,
        }
    return {
        "status": built["status"],
        "resolved_model": built["resolved_model"],
        "fallback": built["fallback"],
        "cost": built["cost"],
        "duration_ms": built["duration_ms"],
        "run_id": built["run_id"],
        "message": built["error"]["message"] if built["error"] else None,
    }


def make_row(model, case, repeat, outcome, error, violation):
    """One result row: what ran, what the reply scored, and what it cost."""
    score = score_run(case, outcome.report if outcome else None)
    row = {
        "model": model,
        "case": case.id,
        "kind": case.kind,
        "repeat": repeat,
        "ran": outcome is not None,
        "valid": score.valid,
        "verdict": score.verdict,
        "blocking": score.blocking,
        "detected": score.detected,
        "line_basis": score.line_basis,
        "false_positive": score.false_positive,
        "violation": violation,
    }
    row.update(_from_record(outcome.record if outcome else None))
    message = row.pop("message")
    row["error"] = error or message
    return row


def run_one(root, case, model, repeat, work, runs_dir, review, timeout):
    """Build the case project, run the review in it, and score it. A run that could not start is a row too."""
    target = bench_cases.build_target(case, work / "target")
    diff = bench_cases.write_diff(case, work / "case.patch")
    before = snapshot(target)
    outcome, error = None, None
    try:
        outcome = review(root, target, ROLE, diff, timeout=timeout)
    except NOT_RUN as problem:
        error = str(problem)
    violation = snapshot(target) != before
    if outcome:
        record.append_record(outcome.record, runs_dir)
    return make_row(model, case, repeat, outcome, error, violation)


def split_spec(spec):
    """'model' or 'model@effort' -> (model, effort or None). The spec is also the label of the model in the results."""
    model, _, effort = spec.partition("@")
    return model, effort or None


def _bench_root(repo_root, directory, spec, trial):
    model, effort = split_spec(spec)
    return make_bench_root(repo_root, directory, model, effort, trial)


def schedule(cases, models, repeats):
    """Repeat by repeat, case by case, model by model, so slow drift hits every model alike."""
    return [(repeat, case, model) for repeat in range(1, repeats + 1) for case in cases for model in models]


def _mark(row):
    if row["false_positive"]:
        return " FALSE POSITIVE"
    if row["detected"] is None:
        return ""
    return " found" if row["detected"] else " MISSED"


def describe_row(row):
    head = f"{row['model']} {row['case']} #{row['repeat']}:"
    if not row["ran"]:
        return f"{head} not run ({row['error']})"
    status = row["status"]
    outcome = f"execution {status['execution']}, artifact {status['artifact']}"
    return f"{head} {outcome}, {row['verdict'] or 'no report'}{_mark(row)}, cost {row['cost']}"


def _append_row(path, row):
    with open(path, "a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(row, sort_keys=True) + "\n")


def run_benchmark(
    repo_root, models, case_ids, repeats, out_dir, review=run.run_review, timeout=run.RUN_TIMEOUT, progress=print,
    trial_models=(),
):
    """Run every model on every case, repeats times. Returns the rows and writes results.jsonl under out_dir."""
    cases = [bench_cases.get_case(case_id) for case_id in case_ids]
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    base = Path(tempfile.mkdtemp(prefix="review-bench-"))
    rows = []
    try:
        roots = {spec: _bench_root(repo_root, base / f"root-{number}", spec, spec in trial_models) for number, spec in enumerate(models)}
        for repeat, case, model in schedule(cases, models, repeats):
            work = Path(tempfile.mkdtemp(prefix="case-", dir=base))
            row = run_one(roots[model], case, model, repeat, work, out / "runs", review, timeout)
            rows.append(row)
            _append_row(out / "results.jsonl", row)
            progress(describe_row(row))
    finally:
        shutil.rmtree(base, ignore_errors=True)
    return rows


def _count(rows, key, value=True):
    return sum(1 for row in rows if row[key] == value)


def stable_cases(rows):
    """(cases whose valid replies all gave one verdict, cases with at least two valid replies)."""
    verdicts = {}
    for row in rows:
        if row["verdict"] is not None:
            verdicts.setdefault(row["case"], []).append(row["verdict"])
    compared = [found for found in verdicts.values() if len(found) >= 2]
    return sum(1 for found in compared if len(set(found)) == 1), len(compared)


def _timing(rows):
    costs = [row["cost"] for row in rows if row["cost"] is not None]
    times = [row["duration_ms"] for row in rows if row["duration_ms"] is not None]
    return {"cost": sum(costs), "mean_ms": sum(times) / len(times) if times else None}


def model_stats(rows):
    bug = [row for row in rows if row["kind"] == "bug"]
    clean = [row for row in rows if row["kind"] == "clean"]
    stats = {
        "runs": len(rows),
        "not_run": _count(rows, "ran", False),
        "valid": _count(rows, "valid"),
        "bug_runs": len(bug),
        "detected": _count(bug, "detected"),
        "line_file": _count(bug, "line_basis", "file"),
        "line_patch": _count(bug, "line_basis", "patch"),
        "clean_runs": len(clean),
        "false_positives": _count(clean, "false_positive"),
        "violations": _count(rows, "violation"),
        "fallbacks": _count(rows, "fallback"),
        "stable": stable_cases(rows),
    }
    stats.update(_timing(rows))
    return stats


def repeats_of(rows):
    """The largest number of runs of one model on one case: the margin of decision #5."""
    counts = {}
    for row in rows:
        key = (row["model"], row["case"])
        counts[key] = counts.get(key, 0) + 1
    return max(counts.values(), default=1)


def review_flags(stats, base, margin):
    """What a person should look at for this model, compared with the baseline (decision #5)."""
    flags = []
    if stats["valid"] < stats["runs"]:
        flags.append(f"{stats['runs'] - stats['valid']} run(s) without a valid report")
    for key, text in (("violations", "changed the target project"), ("fallbacks", "fell back to another agent")):
        if stats[key]:
            flags.append(f"{stats[key]} run(s) {text}")
    missed = stats["bug_runs"] - stats["detected"]
    base_missed = base["bug_runs"] - base["detected"]
    if missed - base_missed > margin:
        flags.append(f"missed {missed - base_missed} more bug run(s) than the baseline (margin {margin})")
    if stats["false_positives"] - base["false_positives"] > margin:
        extra = stats["false_positives"] - base["false_positives"]
        flags.append(f"{extra} more false positive(s) than the baseline (margin {margin})")
    return flags


def summarize(rows, baseline):
    """(stats per model, flags per model, margin). Models keep the order of their first run."""
    by_model = {}
    for row in rows:
        by_model.setdefault(row["model"], []).append(row)
    stats = {model: model_stats(items) for model, items in by_model.items()}
    margin = repeats_of(rows)
    base = stats.get(baseline) or next(iter(stats.values()))
    return stats, {model: review_flags(item, base, margin) for model, item in stats.items()}, margin


def _model_line(model, item):
    mean = f"{item['mean_ms'] / 1000:.0f} s" if item["mean_ms"] is not None else "n/a"
    stable = f"{item['stable'][0]}/{item['stable'][1]}"
    return (
        f"{model}: valid {item['valid']}/{item['runs']}, found {item['detected']}/{item['bug_runs']} "
        f"(cited line = file line {item['line_file']}, patch line {item['line_patch']}), "
        f"false positives {item['false_positives']}/{item['clean_runs']}, stable verdicts {stable}, "
        f"not run {item['not_run']}, violations {item['violations']}, cost ${item['cost']:.3f}, mean {mean}"
    )


def render_summary(rows, baseline):
    stats, flags, margin = summarize(rows, baseline)
    cases = len({row["case"] for row in rows})
    lines = [
        f"Reviewer benchmark: {len(rows)} runs, {len(stats)} models, {cases} cases, margin {margin} run(s) (decision #5)",
        f"Baseline: {baseline}",
        "Found = a BLOCKING finding in the right file whose text names the bug.",
    ]
    for model, item in stats.items():
        lines.append(_model_line(model, item))
        lines += [f"    REVIEW: {flag}" for flag in flags[model]]
    return "\n".join(lines)


def load_rows(path):
    text = Path(path).read_text(encoding="utf-8")
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def build_parser():
    parser = argparse.ArgumentParser(
        prog="python -m execution.runner.benchmark", description="Compare models on the reviewer cases."
    )
    parser.add_argument("--models", default="", help="comma separated model ids to compare with the baseline; model@effort sets a reasoning effort")
    parser.add_argument("--cases", default="", help="comma separated case ids (default: all)")
    parser.add_argument("--repeats", type=int, default=DEFAULT_REPEATS, help="runs per model and case")
    parser.add_argument("--out", default="", help="folder for results.jsonl, summary.txt and the run records")
    parser.add_argument("--repo-root", default=str(REPO_ROOT), help="framework folder with the profile and the policy")
    parser.add_argument("--timeout", type=int, default=run.RUN_TIMEOUT, help="seconds before one run is stopped")
    parser.add_argument("--summarize", default="", help="print the summary of an earlier results.jsonl and stop")
    parser.add_argument("--trial", action="store_true", help="count the --models as approved inside this benchmark only (for models the policy lists as experimental)")
    parser.add_argument("--list-cases", action="store_true", help="list the cases and stop")
    return parser


def _split(text):
    return [part.strip() for part in text.split(",") if part.strip()]


def _default_out():
    return record.DEFAULT_RUNS_DIR / ("bench-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))


def _problem(args):
    unknown = [case_id for case_id in _split(args.cases) if case_id not in bench_cases.CASE_IDS]
    if unknown:
        return f"unknown case(s) {', '.join(unknown)}"
    if args.repeats < 1:
        return "--repeats must be at least 1"
    return None


def _run_from_args(args, review):
    problem = _problem(args)
    if problem:
        print(f"not run: {problem}", file=sys.stderr)
        return 2
    try:
        baseline = resolve.resolve(ROLE, args.repo_root).model
    except resolve.ResolveError as error:
        print(f"not run: {error}", file=sys.stderr)
        return 2
    models = list(dict.fromkeys([baseline] + _split(args.models)))
    case_ids = _split(args.cases) or list(bench_cases.CASE_IDS)
    out = Path(args.out) if args.out else _default_out()
    total = len(models) * len(case_ids) * args.repeats
    print(f"planned {total} runs: {len(models)} models x {len(case_ids)} cases x {args.repeats} repeats; results in {out.as_posix()}")
    trial = set(_split(args.models)) if args.trial else set()
    if trial:
        print("trial models count as approved inside this benchmark only; execution/policy.json is not changed")
    rows = run_benchmark(
        args.repo_root, models, case_ids, args.repeats, out, review=review, timeout=args.timeout, trial_models=trial
    )
    text = render_summary(rows, baseline)
    (out / "summary.txt").write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


def main(argv=None, review=run.run_review):
    args = build_parser().parse_args(argv)
    if args.list_cases:
        print("\n".join(f"{case.id} ({case.kind}): {case.summary}" for case in bench_cases.CASES))
        return 0
    if args.summarize:
        rows = load_rows(args.summarize)
        if not rows:
            print(f"not run: no results in {args.summarize}", file=sys.stderr)
            return 2
        print(render_summary(rows, rows[0]["model"]))
        return 0
    return _run_from_args(args, review)


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(errors="replace")
    sys.exit(main())
