import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from execution.runner import record  # noqa: E402


def fields(**changes):
    base = {
        "role": "code-reviewer",
        "profile": "default",
        "runtime": "rt",
        "requested_model": "m/one",
        "resolved_model": "m/one",
        "policy_result": "pass",
        "fallback": False,
        "input_artifacts": ["diff.patch"],
        "output_artifacts": ["review.json"],
        "status": record.status_levels("success", "success", "success"),
        "stop_reason": "stop",
        "tokens": {"input": 10, "output": 5},
        "cost": 0.01,
        "duration_ms": 1200,
        "verification": None,
        "error": None,
    }
    return dict(base, **changes)


class BuildRecord(unittest.TestCase):
    def test_run_id_and_timestamp_are_filled(self):
        first = record.build_record(**fields())
        second = record.build_record(**fields())
        self.assertTrue(first["run_id"])
        self.assertNotEqual(first["run_id"], second["run_id"])
        self.assertRegex(first["timestamp"], r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")

    def test_given_values_are_kept(self):
        built = record.build_record(run_id="r1", timestamp="2026-10-21T10:00:00Z", **fields())
        self.assertEqual((built["run_id"], built["timestamp"]), ("r1", "2026-10-21T10:00:00Z"))

    def test_a_missing_field_is_named(self):
        broken = fields()
        del broken["role"]
        with self.assertRaisesRegex(record.RecordError, "missing 'role'"):
            record.build_record(**broken)

    def test_an_unknown_field_is_rejected(self):
        with self.assertRaisesRegex(record.RecordError, "unexpected 'extra'"):
            record.build_record(**fields(extra=1))

    def test_a_timestamp_that_is_not_utc_iso_is_rejected(self):
        with self.assertRaisesRegex(record.RecordError, "timestamp"):
            record.build_record(timestamp="../../etc", **fields())

    def test_artifact_success_needs_execution_success(self):
        status = record.status_levels("failure", "success", "not_run")
        with self.assertRaisesRegex(record.RecordError, "artifact cannot succeed unless execution"):
            record.build_record(**fields(status=status, error=record.error_info("boom")))

    def test_workflow_success_needs_artifact_success(self):
        status = record.status_levels("success", "not_run", "success")
        with self.assertRaisesRegex(record.RecordError, "workflow cannot succeed unless artifact"):
            record.build_record(**fields(status=status))

    def test_a_failed_level_needs_an_error_object(self):
        with self.assertRaisesRegex(record.RecordError, "needs an error"):
            record.build_record(**fields(status=record.status_levels("failure")))

    def test_a_failed_run_with_an_error_object_is_valid(self):
        built = record.build_record(
            **fields(
                resolved_model=None,
                status=record.status_levels("failure"),
                error=record.error_info("boom", "err line", ["e1"]),
            )
        )
        self.assertEqual(built["status"]["execution"], "failure")

    def test_a_failed_run_with_a_reply_head_is_valid(self):
        error = record.error_info("boom", reply="start of the reply")
        built = record.build_record(**fields(status=record.status_levels("success", "failure"), error=error))
        self.assertEqual(built["error"]["reply_head"], "start of the reply")

    def test_an_empty_error_message_is_rejected(self):
        with self.assertRaisesRegex(record.RecordError, "message"):
            record.build_record(**fields(status=record.status_levels("failure"), error=record.error_info("")))


class ErrorInfo(unittest.TestCase):
    def test_only_the_last_twenty_lines_are_kept(self):
        stderr = "\n".join(f"line {i}" for i in range(30))
        events = [f"e{i}" for i in range(30)]
        info = record.error_info("boom", stderr, events)
        self.assertEqual(info["stderr_tail"].splitlines(), [f"line {i}" for i in range(10, 30)])
        self.assertEqual(info["event_tail"], [f"e{i}" for i in range(10, 30)])

    def test_the_start_of_a_reply_is_kept_and_cut(self):
        info = record.error_info("boom", reply="## Analysis" + "x" * 3000)
        self.assertTrue(info["reply_head"].startswith("## Analysis"))
        self.assertEqual(len(info["reply_head"]), record.REPLY_CHARS)

    def test_no_reply_means_no_reply_head(self):
        self.assertNotIn("reply_head", record.error_info("boom"))

    def test_long_lines_are_cut_and_events_become_text(self):
        info = record.error_info("boom", "", [{"type": "error"}, "x" * 600])
        self.assertEqual(info["event_tail"][0], str({"type": "error"}))
        self.assertEqual(len(info["event_tail"][1]), 500)
        self.assertEqual(info["stderr_tail"], "")


class StatusLevels(unittest.TestCase):
    def test_every_level_defaults_to_not_run(self):
        self.assertEqual(record.status_levels(), {"execution": "not_run", "artifact": "not_run", "workflow": "not_run"})


class Store(unittest.TestCase):
    def test_to_jsonl_is_one_line_with_sorted_keys_and_round_trips(self):
        built = record.build_record(**fields())
        line = record.to_jsonl(built)
        self.assertNotIn("\n", line)
        self.assertEqual(json.loads(line), built)
        self.assertEqual(list(json.loads(line)), sorted(built))

    def test_append_writes_one_line_per_record_into_a_file_named_by_date(self):
        with tempfile.TemporaryDirectory() as tmp:
            runs = Path(tmp) / "runs"
            first = record.build_record(timestamp="2026-10-21T10:00:00Z", **fields())
            second = record.build_record(timestamp="2026-10-21T11:00:00Z", **fields())
            path = record.append_record(first, runs)
            self.assertEqual(record.append_record(second, runs), path)
            self.assertEqual(path, runs / "2026-10-21.jsonl")
            lines = path.read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(lines), 2)
        self.assertEqual(json.loads(lines[1])["run_id"], second["run_id"])

    def test_an_invalid_record_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            runs = Path(tmp) / "runs"
            bad = record.build_record(**fields())
            bad["role"] = ""
            with self.assertRaises(record.RecordError):
                record.append_record(bad, runs)
            self.assertFalse(runs.exists())

    def test_records_go_under_the_runner_folder_by_default(self):
        self.assertEqual(record.DEFAULT_RUNS_DIR, REPO / "execution" / "runner" / "runs")


if __name__ == "__main__":
    unittest.main()
