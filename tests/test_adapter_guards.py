"""Tests for the directory check and for naming auto-rejected permissions (F74, F75)."""

import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from execution.runner import opencode_adapter as adapter  # noqa: E402

FIXTURES = REPO / "tests" / "fixtures" / "opencode-run"
AGENT = "sample-reviewer"
MODEL = "github-copilot/claude-haiku-4.5"
ASK = "! permission requested: {} ({}); auto-rejecting\n"


def read(name):
    return (FIXTURES / name).read_text(encoding="utf-8")


def export(directory=None, cwd=None):
    info = {"role": "assistant", "agent": AGENT, "providerID": "github-copilot", "modelID": "claude-haiku-4.5", "finish": "stop"}
    if cwd:
        info["path"] = {"cwd": cwd, "root": cwd}
    return json.dumps({"info": {"directory": directory} if directory else {}, "messages": [{"info": info}]})


def ran_in(directory=None):
    return adapter.RanInfo(AGENT, MODEL, "stop", directory=directory)


class ParseDirectory(unittest.TestCase):
    def test_the_message_directory_wins_over_the_session_directory(self):
        self.assertEqual(adapter.parse_export(export("a", "b")).directory, "b")

    def test_the_session_directory_is_the_fallback(self):
        self.assertEqual(adapter.parse_export(export("a")).directory, "a")

    def test_a_captured_export_without_one_gives_none(self):
        self.assertIsNone(adapter.parse_export(read("review-session.json")).directory)


class CheckDirectory(unittest.TestCase):
    def test_nothing_requested_nothing_checked(self):
        self.assertEqual(adapter.check_directory(ran_in(), None), [])

    def test_the_requested_folder_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(adapter.check_directory(ran_in(tmp), Path(tmp)), [])

    def test_another_folder_fails_and_names_both(self):
        with tempfile.TemporaryDirectory() as one, tempfile.TemporaryDirectory() as two:
            problems = adapter.check_directory(ran_in(one), two)
        self.assertEqual(len(problems), 1)
        self.assertIn("F74", problems[0])
        self.assertIn(one, problems[0])

    def test_an_export_without_a_directory_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            problems = adapter.check_directory(ran_in(), tmp)
        self.assertIn("unknown", problems[0])

    def test_a_folder_that_does_not_exist_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(len(adapter.check_directory(ran_in(str(Path(tmp) / "gone")), tmp)), 1)


class Rejections(unittest.TestCase):
    def test_a_rejected_request_is_named(self):
        text = ASK.format("external_directory", "D:\\skills\\sub\\*")
        self.assertEqual(adapter.rejected_permissions(text), ["external_directory (D:\\skills\\sub\\*)"])

    def test_a_long_command_is_cut_and_each_request_is_named_once(self):
        patch = "apply_patch <<'PATCH'\n*** Begin Patch\n" + "+x\n" * 100 + "*** End Patch\nPATCH"
        text = ASK.format("bash", patch) + ASK.format("bash", "echo done") + ASK.format("bash", "echo done")
        found = adapter.rejected_permissions(text)
        self.assertEqual(len(found), 2)
        self.assertTrue(found[0].startswith("bash (apply_patch <<'PATCH' *** Begin Patch"))
        self.assertLessEqual(len(found[0]), 110)
        self.assertEqual(found[1], "bash (echo done)")

    def test_other_stderr_names_nothing(self):
        self.assertEqual(adapter.rejected_permissions("some warning\n"), [])


class AssessWiring(unittest.TestCase):
    def go(self, stderr="", ran=None, **kwargs):
        ran = ran or adapter.parse_export(read("review-session.json"))
        return adapter.assess(adapter.parse_events(read("review.jsonl")), stderr, ran, AGENT, MODEL, **kwargs)

    def test_without_a_requested_directory_the_run_is_as_before(self):
        self.assertEqual(self.go().status, "success")

    def test_the_requested_directory_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(self.go(ran=ran_in(tmp), directory=tmp).status, "success")

    def test_a_session_that_names_no_directory_fails_the_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = self.go(directory=tmp)
        self.assertEqual(result.status, "failure")
        self.assertIn("F74", result.problems[0])

    def test_a_failed_run_names_the_rejected_permission(self):
        events = adapter.parse_events(read("bad-model.jsonl"))
        result = adapter.assess(events, ASK.format("bash", "echo done"), None, AGENT, MODEL, exit_code=1)
        self.assertEqual(result.status, "failure")
        self.assertTrue(any("auto-rejected" in problem and "bash (echo done)" in problem for problem in result.problems))

    def test_a_run_that_succeeded_is_not_changed_by_a_rejection(self):
        self.assertEqual(self.go(stderr=ASK.format("bash", "echo done")).status, "success")


if __name__ == "__main__":
    unittest.main()
