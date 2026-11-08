import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tools"))

from execution.runner import cli, facts, facts_check, record, run  # noqa: E402
from execution.runner.tree import Changes  # noqa: E402

REPORT = {
    "outcome": "TESTS_WRITTEN",
    "summary": "Tested the function.",
    "frameworks": ["node:test"],
    "tests_written": [{"file": "src/a.test.ts", "count": 2, "covers": "the happy path"}],
    "gaps": ["Empty input is not tested."],
    "production_issues": [{"file": "src/a.ts", "message": "Divides by zero."}],
}
PASSED = facts.TestOutcome(0, False, ("ok",), 1)
FAILED = facts.TestOutcome(1, False, ("not ok",), 1)
TIMED_OUT = facts.TestOutcome(-1, True, (), 0, "the tests did not finish within 5 s")


def make_outcome(tests, problems=()):
    workflow = "success" if tests.passed and not problems else "failure"
    verification = facts_check.build_verification("mytests --all", tests, Changes(added=("src/a.test.ts",)), problems)
    built = record.build_record(
        role="qa",
        profile="default",
        runtime="opencode",
        requested_model="m/one",
        resolved_model="m/one",
        policy_result="pass",
        fallback=False,
        input_artifacts=["d.patch"],
        output_artifacts=[],
        status=record.status_levels("success", "success", workflow),
        stop_reason="stop",
        tokens=None,
        cost=0.01,
        duration_ms=5,
        verification=verification,
        error=None if workflow == "success" else record.error_info("the facts failed"),
    )
    return run.Outcome(record=built, report=REPORT)


class QaCli(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.runs = Path(self.tmp.name) / "runs"

    def call(self, outcome):
        out = io.StringIO()
        args = ["--role", "qa", "--target", "t", "--diff", "d.patch"]
        with contextlib.redirect_stdout(out):
            code = cli.main(args, review=lambda *a, **k: outcome, runs_dir=self.runs)
        return code, out.getvalue()

    def stored(self):
        return [line for path in self.runs.glob("*.jsonl") for line in path.read_text(encoding="utf-8").splitlines()]

    def test_a_passing_run_exits_0_and_prints_the_qa_report_and_the_tests(self):
        code, text = self.call(make_outcome(PASSED))
        self.assertEqual(code, 0)
        self.assertIn("outcome: TESTS_WRITTEN (1 test files)", text)
        self.assertIn("src/a.test.ts: 2 tests", text)
        self.assertIn("gap: Empty input is not tested.", text)
        self.assertIn("production issue in src/a.ts: Divides by zero.", text)
        self.assertIn("tests: mytests --all -> exit 0", text)
        self.assertEqual(len(self.stored()), 1)

    def test_failing_tests_exit_1_and_still_store_the_record(self):
        code, text = self.call(make_outcome(FAILED))
        self.assertEqual(code, 1)
        self.assertIn("-> exit 1", text)
        self.assertEqual(len(self.stored()), 1)

    def test_a_timeout_is_shown_and_exits_1(self):
        code, text = self.call(make_outcome(TIMED_OUT))
        self.assertEqual(code, 1)
        self.assertIn("-> timed out", text)

    def test_problems_are_listed_and_exit_1_even_when_the_tests_pass(self):
        code, text = self.call(make_outcome(PASSED, ["src/a.ts was modified but is not in tests_written"]))
        self.assertEqual(code, 1)
        self.assertIn("  problem: src/a.ts was modified but is not in tests_written", text)


if __name__ == "__main__":
    unittest.main()
