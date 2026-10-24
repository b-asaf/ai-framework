import contextlib
import glob
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tools"))

from execution.runner import bench_cases, benchmark, record, resolve, run  # noqa: E402

CASE = bench_cases.get_case("off-by-one-loop")
CLEAN = bench_cases.get_case("clean-rename-helper")
ROLE = bench_cases.ROLE


def report_with(*findings):
    blocking = any(finding["severity"] == "BLOCKING" for finding in findings)
    return {"verdict": "REQUEST CHANGES" if blocking else "APPROVED", "summary": "s", "findings": list(findings)}


def bug_finding(case, **changes):
    file_line, _ = bench_cases.bug_lines(case)
    finding = {
        "severity": "BLOCKING",
        "category": "LOGIC",
        "message": case.bug.example,
        "file": case.bug.file,
        "line": file_line,
    }
    finding.update(changes)
    return finding


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def make_repo(base, models=("m/one", "m/two")):
    root = Path(base) / "repo"
    entry = {"family": "x", "status": "approved", "evaluation": None}
    write_json(root / "execution" / "policy.json", {"version": 1, "models": {m: dict(entry) for m in models}, "constraints": {"independence": []}})
    write_json(root / "execution" / "profiles" / "default.json", {"version": 1, "agents": {ROLE: {"model": models[0]}}})
    (root / "agents").mkdir(parents=True)
    (root / "agents" / f"{ROLE}.md").write_text("---\nmode: subagent\n---\nReview.\n", encoding="utf-8")
    return root


def make_record(model):
    return record.build_record(
        role=ROLE,
        profile="default",
        runtime="opencode",
        requested_model=model,
        resolved_model=model,
        policy_result="pass",
        fallback=False,
        input_artifacts=["case.patch"],
        output_artifacts=[],
        status=record.status_levels("success", "success"),
        stop_reason="stop",
        tokens=None,
        cost=0.01,
        duration_ms=1000,
        verification=None,
        error=None,
    )


class FakeReview:
    """Stands in for run_review: reads the model from the bench root and answers from the case."""

    def __init__(self, detect=True, false_positive=False, write=None, error=None):
        self.detect, self.false_positive, self.write, self.error = detect, false_positive, write, error
        self.models = []
        self.calls = 0

    def __call__(self, root, target, role, diff, timeout=None):
        self.calls += 1
        if self.error:
            raise self.error
        text = Path(diff).read_text(encoding="utf-8")
        case = next(c for c in bench_cases.CASES if bench_cases.make_diff(c.changes) == text)
        profile = json.loads((Path(root) / "execution" / "profiles" / "default.json").read_text(encoding="utf-8"))
        model = profile["agents"][role]["model"]
        self.models.append(model)
        if self.write:
            (Path(target) / self.write).write_text("x", encoding="utf-8")
        return run.Outcome(make_record(model), self.report_for(case))

    def report_for(self, case):
        if case.bug and self.detect:
            return report_with(bug_finding(case))
        if case.bug is None and self.false_positive:
            return report_with({"severity": "BLOCKING", "category": "STYLE", "message": "Invented problem."})
        return report_with()


def row(model, case, kind, **changes):
    base = {
        "model": model,
        "case": case,
        "kind": kind,
        "repeat": 1,
        "ran": True,
        "error": None,
        "status": {"execution": "success", "artifact": "success", "workflow": "not_run"},
        "resolved_model": model,
        "fallback": False,
        "cost": 0.1,
        "duration_ms": 2000,
        "run_id": "r",
        "valid": True,
        "verdict": "APPROVED",
        "blocking": 0,
        "detected": None,
        "line_basis": None,
        "false_positive": None,
        "violation": False,
    }
    base.update(changes)
    return base


def bug_rows(model, found):
    return [row(model, name, "bug", detected=flag) for name, flag in zip("abc", found)]


def clean_rows(model, flags):
    return [row(model, name, "clean", false_positive=flag) for name, flag in zip("xyz", flags)]


class Snapshot(unittest.TestCase):
    def test_changes_additions_and_removals_are_seen_and_git_is_ignored(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a.txt").write_text("one", encoding="utf-8")
            start = benchmark.snapshot(root)
            (root / ".git").mkdir()
            (root / ".git" / "config").write_text("x", encoding="utf-8")
            self.assertEqual(benchmark.snapshot(root), start)
            (root / "a.txt").write_text("two", encoding="utf-8")
            self.assertNotEqual(benchmark.snapshot(root), start)
            (root / "a.txt").write_text("one", encoding="utf-8")
            (root / "b.txt").write_text("x", encoding="utf-8")
            self.assertNotEqual(benchmark.snapshot(root), start)
            (root / "b.txt").unlink()
            (root / "a.txt").unlink()
            self.assertNotEqual(benchmark.snapshot(root), start)


class BenchRoot(unittest.TestCase):
    def test_two_models_differ_only_in_the_profile(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = make_repo(tmp)
            one = benchmark.make_bench_root(repo, Path(tmp) / "one", "m/one")
            two = benchmark.make_bench_root(repo, Path(tmp) / "two", "m/two")
            first, second = benchmark.snapshot(one), benchmark.snapshot(two)
            self.assertEqual(sorted(first), sorted(second))
            self.assertEqual([path for path in first if first[path] != second[path]], ["execution/profiles/default.json"])
            self.assertEqual(resolve.resolve(ROLE, one).model, "m/one")
            self.assertEqual(resolve.resolve(ROLE, two).model, "m/two")


class Scoring(unittest.TestCase):
    def test_a_bug_found_with_the_line_of_the_file(self):
        score = benchmark.score_run(CASE, report_with(bug_finding(CASE)))
        self.assertEqual((score.valid, score.detected, score.line_basis, score.blocking), (True, True, "file", 1))
        self.assertIsNone(score.false_positive)

    def test_a_bug_found_with_the_line_of_the_patch(self):
        file_line, patch_line = bench_cases.bug_lines(CASE)
        self.assertNotEqual(file_line, patch_line)
        score = benchmark.score_run(CASE, report_with(bug_finding(CASE, line=patch_line)))
        self.assertEqual((score.detected, score.line_basis), (True, "patch"))

    def test_a_bug_found_with_another_line_has_no_line_basis(self):
        score = benchmark.score_run(CASE, report_with(bug_finding(CASE, line=99)))
        self.assertEqual((score.detected, score.line_basis), (True, None))

    def test_a_path_with_a_diff_prefix_still_counts(self):
        score = benchmark.score_run(CASE, report_with(bug_finding(CASE, file="b/" + CASE.bug.file)))
        self.assertTrue(score.detected)

    def test_a_non_blocking_finding_does_not_count(self):
        score = benchmark.score_run(CASE, report_with(bug_finding(CASE, severity="NON-BLOCKING")))
        self.assertEqual((score.detected, score.blocking), (False, 0))

    def test_a_finding_in_another_file_does_not_count(self):
        self.assertFalse(benchmark.score_run(CASE, report_with(bug_finding(CASE, file="src/other.ts"))).detected)

    def test_a_finding_that_does_not_name_the_bug_does_not_count(self):
        finding = bug_finding(CASE, message="Rename this variable to something clearer.")
        self.assertFalse(benchmark.score_run(CASE, report_with(finding)).detected)

    def test_no_report_finds_nothing(self):
        score = benchmark.score_run(CASE, None)
        self.assertEqual(score, benchmark.Score(False, None, 0, False, None, None))

    def test_a_clean_diff_that_is_approved_is_not_a_false_positive(self):
        self.assertFalse(benchmark.score_run(CLEAN, report_with()).false_positive)

    def test_a_clean_diff_with_only_a_non_blocking_note_is_not_a_false_positive(self):
        note = {"severity": "NON-BLOCKING", "category": "NAMING", "message": "Unclear."}
        self.assertFalse(benchmark.score_run(CLEAN, report_with(note)).false_positive)

    def test_a_clean_diff_that_is_blocked_is_a_false_positive(self):
        blocked = report_with({"severity": "BLOCKING", "category": "STYLE", "message": "x"})
        score = benchmark.score_run(CLEAN, blocked)
        self.assertEqual((score.false_positive, score.detected, score.blocking), (True, None, 1))

    def test_a_clean_diff_without_a_report_is_invalid_but_not_a_false_positive(self):
        score = benchmark.score_run(CLEAN, None)
        self.assertEqual((score.valid, score.false_positive), (False, False))


class Schedule(unittest.TestCase):
    def test_repeat_then_case_then_model(self):
        cases = [CASE, CLEAN]
        plan = [(repeat, case.id, model) for repeat, case, model in benchmark.schedule(cases, ["m1", "m2"], 2)]
        self.assertEqual(len(plan), 8)
        self.assertEqual(plan[:4], [(1, CASE.id, "m1"), (1, CASE.id, "m2"), (1, CLEAN.id, "m1"), (1, CLEAN.id, "m2")])
        self.assertEqual(plan[4][0], 2)


class RunBenchmark(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = make_repo(self.tmp.name)
        self.out = Path(self.tmp.name) / "out"

    def go(self, review, repeats=2, cases=("off-by-one-loop", "clean-rename-helper")):
        lines = []
        rows = benchmark.run_benchmark(
            self.repo, ["m/one", "m/two"], list(cases), repeats, self.out, review=review, progress=lines.append
        )
        return rows, lines

    def test_every_model_runs_every_case_every_repeat_and_everything_is_stored(self):
        fake = FakeReview()
        rows, lines = self.go(fake)
        self.assertEqual((len(rows), len(lines), fake.calls), (8, 8, 8))
        stored = (self.out / "results.jsonl").read_text(encoding="utf-8").splitlines()
        self.assertEqual([json.loads(line) for line in stored], rows)
        records = [line for path in (self.out / "runs").glob("*.jsonl") for line in path.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(len(records), 8)

    def test_each_model_runs_on_a_bench_root_that_names_it(self):
        fake = FakeReview()
        self.go(fake)
        self.assertEqual(sorted(set(fake.models)), ["m/one", "m/two"])
        self.assertEqual(fake.models.count("m/one"), 4)

    def test_rows_are_scored(self):
        rows, _ = self.go(FakeReview())
        bug = [r for r in rows if r["kind"] == "bug"]
        clean = [r for r in rows if r["kind"] == "clean"]
        self.assertTrue(all(r["detected"] and r["line_basis"] == "file" for r in bug))
        self.assertTrue(all(r["false_positive"] is False for r in clean))
        self.assertTrue(all(r["ran"] and r["valid"] and not r["violation"] for r in rows))

    def test_a_missed_bug_and_a_false_positive_are_scored(self):
        rows, _ = self.go(FakeReview(detect=False, false_positive=True), repeats=1)
        self.assertTrue(all(r["detected"] is False for r in rows if r["kind"] == "bug"))
        self.assertTrue(all(r["false_positive"] for r in rows if r["kind"] == "clean"))

    def test_a_run_that_could_not_start_is_a_row_without_a_record(self):
        rows, lines = self.go(FakeReview(error=resolve.ResolveError("no entry")), repeats=1)
        self.assertTrue(all(not r["ran"] and not r["valid"] and r["error"] == "no entry" for r in rows))
        self.assertIn("not run (no entry)", lines[0])
        self.assertFalse((self.out / "runs").exists())

    def test_a_run_that_changes_the_target_is_a_violation(self):
        rows, _ = self.go(FakeReview(write="stray.txt"), repeats=1)
        self.assertTrue(all(r["violation"] for r in rows))

    def test_nothing_is_left_in_the_temp_folder(self):
        pattern = str(Path(tempfile.gettempdir()) / "review-bench-*")
        before = len(glob.glob(pattern))
        self.go(FakeReview(), repeats=1)
        self.assertEqual(len(glob.glob(pattern)), before)

    def test_an_unknown_case_never_starts_a_run(self):
        fake = FakeReview()
        with self.assertRaisesRegex(ValueError, "unknown case"):
            benchmark.run_benchmark(self.repo, ["m/one"], ["nope"], 1, self.out, review=fake)
        self.assertEqual(fake.calls, 0)


class Summary(unittest.TestCase):
    def test_a_model_that_misses_more_than_the_margin_is_flagged_and_a_close_one_is_not(self):
        rows = bug_rows("base", [True, True, True]) + bug_rows("ok", [False, True, True]) + bug_rows("weak", [False] * 3)
        stats, flags, margin = benchmark.summarize(rows, "base")
        self.assertEqual(margin, 1)
        self.assertEqual(flags["base"], [])
        self.assertEqual(flags["ok"], [])
        self.assertIn("missed 3 more bug run(s)", flags["weak"][0])
        self.assertEqual((stats["weak"]["detected"], stats["weak"]["bug_runs"]), (0, 3))

    def test_more_false_positives_than_the_margin_are_flagged(self):
        rows = clean_rows("base", [False, False, False]) + clean_rows("noisy", [True, True, False])
        _, flags, _ = benchmark.summarize(rows, "base")
        self.assertEqual(flags["base"], [])
        self.assertIn("2 more false positive(s)", flags["noisy"][0])

    def test_invalid_reports_violations_and_fallbacks_are_flagged(self):
        rows = [row("m", "a", "bug", valid=False, detected=False, violation=True, fallback=True)]
        _, flags, _ = benchmark.summarize(rows, "m")
        text = " | ".join(flags["m"])
        self.assertIn("without a valid report", text)
        self.assertIn("changed the target project", text)
        self.assertIn("fell back", text)

    def test_the_margin_is_the_number_of_repeats(self):
        rows = [row("m", "a", "bug", repeat=n) for n in (1, 2, 3)] + [row("m", "b", "bug")]
        self.assertEqual(benchmark.repeats_of(rows), 3)
        self.assertEqual(benchmark.repeats_of([]), 1)

    def test_stable_verdicts_are_counted_per_case(self):
        rows = [
            row("m", "a", "bug", verdict="APPROVED"),
            row("m", "a", "bug", verdict="REQUEST CHANGES"),
            row("m", "b", "bug", verdict="APPROVED"),
            row("m", "b", "bug", verdict="APPROVED"),
            row("m", "c", "bug", verdict="APPROVED"),
        ]
        self.assertEqual(benchmark.stable_cases(rows), (1, 2))

    def test_the_text_names_the_baseline_the_models_and_the_flags(self):
        rows = bug_rows("base", [True] * 3) + bug_rows("weak", [False] * 3)
        text = benchmark.render_summary(rows, "base")
        self.assertIn("Baseline: base", text)
        self.assertIn("weak: valid 3/3, found 0/3", text)
        self.assertIn("REVIEW: missed", text)

    def test_a_row_is_described_whether_or_not_it_ran(self):
        found = benchmark.describe_row(row("m/one", "a", "bug", detected=True))
        self.assertIn("m/one a #1", found)
        self.assertIn("found", found)
        missed = benchmark.describe_row(row("m/one", "a", "bug", detected=False))
        self.assertIn("MISSED", missed)
        self.assertIn("not run (boom)", benchmark.describe_row(row("m/one", "a", "bug", ran=False, error="boom")))


class Main(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = make_repo(self.tmp.name)
        self.out = Path(self.tmp.name) / "out"

    def call(self, argv, review=None):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = benchmark.main(argv, review=review or FakeReview())
        return code, out.getvalue(), err.getvalue()

    def test_the_cases_can_be_listed(self):
        code, out, _ = self.call(["--list-cases"])
        self.assertEqual(code, 0)
        for case_id in bench_cases.CASE_IDS:
            self.assertIn(case_id, out)

    def test_a_full_run_stores_the_results_and_prints_the_summary(self):
        argv = ["--repo-root", str(self.repo), "--models", "m/two", "--cases", "off-by-one-loop", "--repeats", "1", "--out", str(self.out)]
        code, out, _ = self.call(argv)
        self.assertEqual(code, 0)
        self.assertIn("planned 2 runs", out)
        self.assertIn("Baseline: m/one", out)
        self.assertEqual(len((self.out / "results.jsonl").read_text(encoding="utf-8").splitlines()), 2)
        self.assertTrue((self.out / "summary.txt").is_file())

    def test_an_unknown_case_or_zero_repeats_does_not_run(self):
        fake = FakeReview()
        for argv, message in ((["--cases", "nope"], "unknown case"), (["--repeats", "0"], "at least 1")):
            with self.subTest(argv=argv):
                code, _, err = self.call(argv + ["--repo-root", str(self.repo)], review=fake)
                self.assertEqual(code, 2)
                self.assertIn(message, err)
        self.assertEqual(fake.calls, 0)

    def test_a_baseline_that_cannot_be_resolved_does_not_run(self):
        (self.repo / "execution" / "profiles" / "default.json").unlink()
        fake = FakeReview()
        code, _, err = self.call(["--repo-root", str(self.repo)], review=fake)
        self.assertEqual((code, fake.calls), (2, 0))
        self.assertIn("not run", err)

    def test_an_earlier_result_file_can_be_summarized(self):
        path = Path(self.tmp.name) / "results.jsonl"
        rows = bug_rows("m/one", [True, True, True])
        path.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
        code, out, _ = self.call(["--summarize", str(path)])
        self.assertEqual(code, 0)
        self.assertIn("Baseline: m/one", out)

    def test_an_empty_result_file_is_refused(self):
        path = Path(self.tmp.name) / "results.jsonl"
        path.write_text("", encoding="utf-8")
        code, _, err = self.call(["--summarize", str(path)])
        self.assertEqual(code, 2)
        self.assertIn("no results", err)


if __name__ == "__main__":
    unittest.main()
