import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tools"))

from execution.runner import cli, opencode_adapter, preflight, record, resolve, run  # noqa: E402
from lib.opencode_resolved import ResolvedModelError  # noqa: E402

REPORT = {
    "verdict": "REQUEST CHANGES",
    "summary": "x",
    "findings": [
        {"severity": "BLOCKING", "category": "LOGIC", "message": "Off by one.", "file": "src/total.ts", "line": 3},
        {"severity": "NON-BLOCKING", "category": "NAMING", "message": "Unclear."},
    ],
}


def make_record(status, error=None):
    return record.build_record(
        role="code-reviewer",
        profile="default",
        runtime="opencode",
        requested_model="m/one",
        resolved_model="m/one",
        policy_result="pass",
        fallback=False,
        input_artifacts=["d.patch"],
        output_artifacts=[],
        status=status,
        stop_reason="stop",
        tokens=None,
        cost=0.01,
        duration_ms=5,
        verification=None,
        error=error,
    )


class Review:
    """Stands in for run_review: returns an Outcome or raises, and remembers how it was called."""

    def __init__(self, result):
        self.result = result
        self.calls = []

    def __call__(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


class Cli(unittest.TestCase):
    ARGS = ["--role", "code-reviewer", "--target", "t", "--diff", "d.patch"]

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.runs = Path(self.tmp.name) / "runs"

    def call(self, review, extra=()):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = cli.main(self.ARGS + list(extra), review=review, runs_dir=self.runs)
        return code, out.getvalue(), err.getvalue()

    def stored(self):
        if not self.runs.exists():
            return []
        return [line for path in self.runs.glob("*.jsonl") for line in path.read_text(encoding="utf-8").splitlines()]

    def test_a_successful_run_exits_0_prints_the_verdict_and_stores_the_record(self):
        outcome = run.Outcome(make_record(record.status_levels("success", "success")), REPORT)
        code, out, _ = self.call(Review(outcome))
        self.assertEqual(code, 0)
        self.assertIn("artifact success", out)
        self.assertIn("verdict: REQUEST CHANGES (2 findings)", out)
        self.assertIn("BLOCKING [LOGIC] src/total.ts:3", out)
        self.assertIn("NON-BLOCKING [NAMING] (no file)", out)
        self.assertEqual(len(self.stored()), 1)

    def test_an_artifact_failure_exits_1_and_still_stores_the_record(self):
        built = make_record(record.status_levels("success", "failure"), record.error_info("the reply is not one JSON object"))
        code, out, _ = self.call(Review(run.Outcome(built, None)))
        self.assertEqual(code, 1)
        self.assertIn("artifact failure", out)
        self.assertIn("error: the reply is not one JSON object", out)
        self.assertEqual(len(self.stored()), 1)

    def test_an_execution_failure_exits_1(self):
        built = make_record(record.status_levels("failure"), record.error_info("Model not found"))
        code, out, _ = self.call(Review(run.Outcome(built, None)))
        self.assertEqual(code, 1)
        self.assertIn("execution failure", out)

    def test_a_run_that_could_not_start_exits_2_and_stores_nothing(self):
        errors = [
            resolve.ResolveError("no entry"),
            preflight.PreflightError("not ready"),
            opencode_adapter.AdapterError("no diff"),
            ResolvedModelError("no opencode"),
        ]
        for error in errors:
            with self.subTest(error=str(error)):
                code, out, err = self.call(Review(error))
                self.assertEqual(code, 2)
                self.assertEqual(out, "")
                self.assertIn(f"not run: {error}", err)
        self.assertEqual(self.stored(), [])

    def test_the_arguments_are_passed_on(self):
        review = Review(run.Outcome(make_record(record.status_levels("success", "success")), REPORT))
        self.call(review)
        args, kwargs = review.calls[0]
        self.assertEqual(args, (str(cli.REPO_ROOT), "t", "code-reviewer", "d.patch"))
        self.assertEqual(kwargs, {"profile_name": "default", "timeout": run.RUN_TIMEOUT})

    def test_the_repo_root_the_profile_and_the_timeout_can_be_changed(self):
        review = Review(run.Outcome(make_record(record.status_levels("success", "success")), REPORT))
        self.call(review, ["--repo-root", "r", "--profile", "bench", "--timeout", "30"])
        args, kwargs = review.calls[0]
        self.assertEqual(args[0], "r")
        self.assertEqual(kwargs, {"profile_name": "bench", "timeout": 30})

    def test_a_missing_required_argument_exits_2_without_running(self):
        review = Review(None)
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as caught:
                cli.main(["--role", "code-reviewer"], review=review, runs_dir=self.runs)
        self.assertEqual(caught.exception.code, 2)
        self.assertEqual(review.calls, [])


if __name__ == "__main__":
    unittest.main()
