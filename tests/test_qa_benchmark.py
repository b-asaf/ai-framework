import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tools"))

from execution.runner import benchmark, facts, facts_check, qa_benchmark, qa_cases, record, resolve, run, tree  # noqa: E402

CASE = qa_cases.get_case("percent-zero-total")
TEST_FILE = "src/percent.test.ts"


def report(outcome):
    written = [{"file": TEST_FILE, "count": 2, "covers": "percent"}] if outcome == "TESTS_WRITTEN" else []
    gaps = ["which rounding?"] if outcome == "NEEDS_DEVELOPER" else []
    return {"outcome": outcome, "summary": "s", "frameworks": ["node:test"], "tests_written": written, "gaps": gaps,
            "production_issues": []}


def make_outcome(model, added=(TEST_FILE,), modified=(), files="default", exit_code=0, outcome="TESTS_WRITTEN"):
    tests = facts.TestOutcome(exit_code, False, ("ok",), 1)
    verification = facts_check.build_verification("node --test", tests, tree.Changes(added=tuple(added), modified=tuple(modified)), [])
    built = record.build_record(
        role="qa", profile="default", runtime="opencode", requested_model=model, resolved_model=model,
        policy_result="pass", fallback=False, input_artifacts=["case.patch"], output_artifacts=[],
        status=record.status_levels("success", "success", "success"), stop_reason="stop", tokens=None, cost=0.01,
        duration_ms=1000, verification=verification, error=None,
    )
    files = {name: "t" for name in added} if files == "default" else files
    return run.Outcome(built, report(outcome), files=files)


class FakeQa:
    def __init__(self, **kwargs):
        self.kwargs, self.models = kwargs, []

    def __call__(self, root, target, role, diff, timeout=None):
        profile = json.loads((Path(root) / "execution" / "profiles" / "default.json").read_text(encoding="utf-8"))
        model = profile["agents"][role]["model"]
        self.models.append(model)
        return make_outcome(model, **self.kwargs)


class FakeTests:
    """Stands in for the test run on the mutant."""

    def __init__(self, code):
        self.code, self.calls = code, []

    def __call__(self, argv, **kwargs):
        cwd = Path(kwargs["cwd"])
        self.calls.append({"cwd": cwd, "test": (cwd / TEST_FILE).read_text(encoding="utf-8") if (cwd / TEST_FILE).exists() else None,
                           "source": (cwd / CASE.path).read_text(encoding="utf-8") if (cwd / CASE.path).exists() else None})
        return SimpleNamespace(returncode=self.code, stdout="x")


def one(review, tests, tmp):
    return qa_benchmark.run_one("root", CASE, "m/one", 1, Path(tmp), Path(tmp) / "runs", review, 5, tests, lambda name: "node")


def make_repo(base):
    root = Path(base) / "repo"
    entry = {"family": "x", "status": "approved", "evaluation": None}
    for rel, data in (("execution/policy.json", {"version": 1, "models": {m: dict(entry) for m in ("m/one", "m/two")}, "constraints": {"independence": []}}),
                      ("execution/profiles/default.json", {"version": 1, "agents": {"qa": {"model": "m/one"}}})):
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(json.dumps(data), encoding="utf-8")
    (root / "agents").mkdir(parents=True, exist_ok=True)
    (root / "agents" / "qa.md").write_text("---\nmode: subagent\n---\nWrite tests.\n", encoding="utf-8")
    return root


class Scoring(unittest.TestCase):
    def row(self, tests_code=1, **kwargs):
        with tempfile.TemporaryDirectory() as tmp:
            tests = FakeTests(tests_code)
            return one(lambda *a, **k: make_outcome("m/one", **kwargs), tests, tmp), tests

    def test_good_tests_that_catch_the_mutant_pass(self):
        row, tests = self.row(1)
        self.assertTrue(row["passed"])
        self.assertEqual(row["production_changed"], [])
        self.assertEqual(len(tests.calls), 1)

    def test_the_mutant_gets_the_written_test_and_the_planted_defect(self):
        _, tests = self.row(1)
        self.assertEqual(tests.calls[0]["test"], "t")
        self.assertEqual(tests.calls[0]["source"], CASE.mutant)

    def test_tests_that_pass_on_the_mutant_do_not_pass(self):
        row, _ = self.row(0)
        self.assertFalse(row["passed"])
        self.assertIs(row["catches_mutant"], False)
        self.assertIn("tests do not catch the mutant", qa_benchmark.why_not(row))

    def test_a_changed_production_file_does_not_pass(self):
        row, _ = self.row(1, modified=(CASE.path,))
        self.assertFalse(row["passed"])
        self.assertEqual(row["production_changed"], [CASE.path])

    def test_no_test_file_does_not_pass(self):
        row, _ = self.row(1, added=(), files={})
        self.assertFalse(row["wrote_tests"])
        self.assertFalse(row["passed"])

    def test_tests_that_fail_on_the_correct_code_skip_the_mutant(self):
        row, tests = self.row(1, exit_code=1)
        self.assertIs(row["passes_on_correct"], False)
        self.assertIsNone(row["catches_mutant"])
        self.assertEqual(tests.calls, [])

    def test_a_file_whose_text_was_not_captured_does_not_pass(self):
        row, tests = self.row(1, files={TEST_FILE: None})
        self.assertIsNone(row["catches_mutant"])
        self.assertIn("the tests could not be run on the mutant", qa_benchmark.why_not(row))
        self.assertFalse(row["passed"])
        self.assertEqual(tests.calls, [])

    def test_needs_developer_is_not_a_pass_and_is_counted_on_its_own(self):
        row, _ = self.row(1, added=(), files={}, outcome="NEEDS_DEVELOPER")
        self.assertFalse(row["passed"])
        self.assertEqual(qa_benchmark.model_stats([row])["refused"], 1)


class RunBenchmark(unittest.TestCase):
    def test_every_model_runs_every_case_and_everything_is_stored(self):
        with tempfile.TemporaryDirectory() as tmp:
            review = FakeQa()
            out = Path(tmp) / "out"
            rows = qa_benchmark.run_qa_benchmark(
                make_repo(tmp), ["m/one", "m/two"], list(qa_cases.CASE_IDS), 1, out, review=review,
                progress=lambda line: None, runner=FakeTests(1), which=lambda name: "node",
            )
            stored = [json.loads(line) for line in (out / "results.jsonl").read_text(encoding="utf-8").splitlines()]
            self.assertEqual(len(rows), 4)
            self.assertEqual(stored, rows)
            self.assertEqual(sorted(review.models), ["m/one", "m/one", "m/two", "m/two"])
            self.assertTrue(all(row["passed"] for row in rows), [qa_benchmark.why_not(row) for row in rows])
            summary = qa_benchmark.render_summary(rows, "m/one")
            self.assertIn("m/two: passed 2/2", summary)

    def test_a_bench_root_for_qa_names_the_model_and_the_agent(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = benchmark.make_bench_root(make_repo(tmp), Path(tmp) / "r", "m/two", role="qa")
            self.assertEqual(resolve.resolve("qa", root).model, "m/two")
            self.assertTrue((root / "agents" / "qa.md").is_file())


if __name__ == "__main__":
    unittest.main()
