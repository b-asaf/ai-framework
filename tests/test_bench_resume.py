import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tools"))

from execution.runner import bench_cases, benchmark, resolve, run  # noqa: E402
from tests.test_benchmark import FakeReview, bug_rows, make_record, make_repo, row  # noqa: E402

HUNG = "OpenCode did not finish within 600 s; OpenCode exited with code -1"


class Suspect(unittest.TestCase):
    def test_a_slept_run_and_a_timeout_are_suspect_and_a_normal_run_is_not(self):
        self.assertTrue(benchmark.suspect(row("m", "a", "bug", slept=True)))
        self.assertTrue(benchmark.suspect(row("m", "a", "bug", error=HUNG)))
        self.assertFalse(benchmark.suspect(row("m", "a", "bug")))
        self.assertFalse(benchmark.suspect(row("m", "a", "bug", error="no text event")))

    def test_suspect_runs_are_left_out_of_the_numbers_and_counted(self):
        rows = bug_rows("base", [True, True, True]) + [row("base", "d", "bug", valid=False, detected=False, slept=True)]
        stats, _, _ = benchmark.summarize(rows, "base")
        self.assertEqual((stats["base"]["runs"], stats["base"]["valid"]), (3, 3))
        self.assertIn("Excluded 1 run(s)", benchmark.render_summary(rows, "base"))

    def test_a_summary_of_only_suspect_runs_does_not_fail(self):
        rows = [row("base", "a", "bug", error=HUNG, valid=False)]
        self.assertIn("Excluded 1 run(s)", benchmark.render_summary(rows, "base"))

    def test_a_row_carries_the_slept_flag_of_the_outcome(self):
        case = bench_cases.get_case("off-by-one-loop")
        outcome = run.Outcome(make_record("m"), None, True)
        self.assertTrue(benchmark.make_row("m", case, 1, outcome, None, False)["slept"])
        self.assertFalse(benchmark.make_row("m", case, 1, None, "x", False)["slept"])


class Resume(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = make_repo(self.tmp.name)
        self.out = Path(self.tmp.name) / "out"
        self.out.mkdir()

    def go(self, review, **kwargs):
        lines = []
        rows = benchmark.run_benchmark(
            self.repo, ["m/one"], ["off-by-one-loop"], 2, self.out, review=review, progress=lines.append, **kwargs
        )
        return rows, lines

    def write_earlier(self):
        good = row("m/one", "off-by-one-loop", "bug", repeat=1, detected=True)
        hung = row("m/one", "off-by-one-loop", "bug", repeat=2, valid=False, error=HUNG)
        (self.out / "results.jsonl").write_text("".join(json.dumps(r) + "\n" for r in (good, hung)), encoding="utf-8")

    def test_resume_repeats_only_the_suspect_rows(self):
        self.write_earlier()
        fake = FakeReview()
        rows, _ = self.go(fake, resume=True)
        self.assertEqual(fake.calls, 1)
        self.assertEqual([(r["repeat"], benchmark.suspect(r)) for r in rows], [(1, False), (2, False)])
        stored = benchmark.load_rows(self.out / "results.jsonl")
        self.assertEqual(len(stored), 2)
        self.assertFalse(any(benchmark.suspect(r) for r in stored))

    def test_without_resume_everything_runs(self):
        fake = FakeReview()
        self.go(fake)
        self.assertEqual(fake.calls, 2)

    def test_resume_without_an_earlier_file_runs_everything(self):
        fake = FakeReview()
        self.go(fake, resume=True)
        self.assertEqual(fake.calls, 2)

    def test_the_flag_is_off_by_default(self):
        self.assertTrue(benchmark.build_parser().parse_args(["--resume"]).resume)
        self.assertFalse(benchmark.build_parser().parse_args([]).resume)


class EarlyStop(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = make_repo(self.tmp.name)

    def go(self, review):
        lines = []
        rows = benchmark.run_benchmark(
            self.repo, ["m/one", "m/two"], ["off-by-one-loop", "leap-year-century"], 3,
            Path(self.tmp.name) / "out", review=review, progress=lines.append,
        )
        return rows, lines

    def test_it_stops_when_the_first_runs_all_fail_to_start(self):
        fake = FakeReview(error=resolve.ResolveError("no entry"))
        rows, lines = self.go(fake)
        self.assertEqual((len(rows), fake.calls), (5, 5))
        self.assertIn("stopping", lines[-1])

    def test_it_keeps_going_when_the_runs_answer(self):
        fake = FakeReview()
        rows, _ = self.go(fake)
        self.assertEqual((len(rows), fake.calls), (12, 12))


if __name__ == "__main__":
    unittest.main()
