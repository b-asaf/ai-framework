import sys
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from execution.verification.checks.quick_lane import (  # noqa: E402
    QuickLaneError,
    RESTRICTED_PATTERNS,
    find_quick_lane_commits,
    find_violations,
    is_quick_lane_message,
    read_commit_measurement,
    read_commits_in_range,
    read_empty_tree,
    read_limits,
    run_git,
)


def failing_runner(*args, **kwargs):
    raise AssertionError("run_git should not have been called")


class IsQuickLaneMessage(unittest.TestCase):
    def test_exact_trailer_line_detected(self):
        self.assertTrue(is_quick_lane_message("feat: x\n\nLane: quick\n"))

    def test_trailer_with_leading_whitespace_detected(self):
        self.assertTrue(is_quick_lane_message("feat: x\n\n  Lane: quick\n"))

    def test_no_trailer_not_detected(self):
        self.assertFalse(is_quick_lane_message("feat: x\n\nsome other line\n"))

    def test_trailer_as_substring_mid_line_not_detected(self):
        self.assertFalse(is_quick_lane_message("see Lane: quick elsewhere in a sentence"))

    def test_wrong_case_not_detected(self):
        self.assertFalse(is_quick_lane_message("lane: quick"))


class FindQuickLaneCommits(unittest.TestCase):
    def test_filters_to_tagged_commits_only(self):
        commits = [("a1", "feat: x\n\nLane: quick\n"), ("a2", "feat: y\n")]
        result = find_quick_lane_commits(commits)
        self.assertEqual([sha for sha, _ in result], ["a1"])


class FindViolations(unittest.TestCase):
    def test_within_limits_is_clean(self):
        measurements = [{"sha": "a1", "files": 2, "lines": 10, "paths": ["a.py", "b.py"]}]
        self.assertEqual(find_violations(measurements, RESTRICTED_PATTERNS, 3, 60), [])

    def test_too_many_files_is_a_violation(self):
        measurements = [{"sha": "a1", "files": 4, "lines": 10, "paths": ["a", "b", "c", "d"]}]
        violations = find_violations(measurements, RESTRICTED_PATTERNS, 3, 60)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["reason"], "quick_lane_over_limit")
        self.assertIn("4 files changed (limit 3)", violations[0]["details"])

    def test_too_many_lines_is_a_violation(self):
        measurements = [{"sha": "a1", "files": 1, "lines": 61, "paths": ["a.py"]}]
        violations = find_violations(measurements, RESTRICTED_PATTERNS, 3, 60)
        self.assertEqual(len(violations), 1)
        self.assertIn("61 lines changed (limit 60)", violations[0]["details"])

    def test_restricted_path_is_a_violation_even_when_tiny(self):
        measurements = [{"sha": "a1", "files": 1, "lines": 1, "paths": ["package.json"]}]
        violations = find_violations(measurements, RESTRICTED_PATTERNS, 3, 60)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["restricted"], ["package.json"])

    def test_restricted_config_file_is_a_violation(self):
        measurements = [{"sha": "a1", "files": 1, "lines": 1, "paths": [".ai-framework.json"]}]
        violations = find_violations(measurements, RESTRICTED_PATTERNS, 3, 60)
        self.assertEqual(len(violations), 1)

    def test_multiple_measurements_each_judged_independently(self):
        measurements = [
            {"sha": "a1", "files": 1, "lines": 1, "paths": ["a.py"]},
            {"sha": "a2", "files": 10, "lines": 1, "paths": ["a.py"]},
        ]
        violations = find_violations(measurements, RESTRICTED_PATTERNS, 3, 60)
        self.assertEqual([v["sha"] for v in violations], ["a2"])

    def test_empty_measurements_is_clean(self):
        self.assertEqual(find_violations([], RESTRICTED_PATTERNS, 3, 60), [])


class ReadLimits(unittest.TestCase):
    def test_no_config_uses_defaults(self):
        self.assertEqual(read_limits(None), (3, 60))

    def test_empty_config_uses_defaults(self):
        self.assertEqual(read_limits({}), (3, 60))

    def test_valid_override(self):
        self.assertEqual(read_limits({"quickLane": {"maxFiles": 1, "maxLines": 5}}), (1, 5))

    def test_partial_override_falls_back_to_default(self):
        self.assertEqual(read_limits({"quickLane": {"maxFiles": 1}}), (1, 60))

    def test_non_positive_int_raises(self):
        with self.assertRaises(QuickLaneError):
            read_limits({"quickLane": {"maxFiles": 0}})

    def test_non_int_raises(self):
        with self.assertRaises(QuickLaneError):
            read_limits({"quickLane": {"maxFiles": "three"}})

    def test_bool_raises(self):
        with self.assertRaises(QuickLaneError):
            read_limits({"quickLane": {"maxFiles": True}})

    def test_quick_lane_not_a_dict_raises(self):
        with self.assertRaises(QuickLaneError):
            read_limits({"quickLane": "oops"})

    def test_config_not_a_dict_raises(self):
        with self.assertRaises(QuickLaneError):
            read_limits(["quickLane"])


class ReadEmptyTree(unittest.TestCase):
    def test_strips_and_returns_output(self):
        fake_run_git = mock.Mock(return_value="4b825dc642cb6eb9a060e54bf8d69288fbee4904\n")
        self.assertEqual(
            read_empty_tree(run_git=fake_run_git),
            "4b825dc642cb6eb9a060e54bf8d69288fbee4904",
        )

    def test_blank_output_raises(self):
        fake_run_git = mock.Mock(return_value="")
        with self.assertRaises(QuickLaneError):
            read_empty_tree(run_git=fake_run_git)


class ReadCommitsInRange(unittest.TestCase):
    def test_parses_sha_and_message_pairs(self):
        output = "sha1\x00msg1\x03sha2\x00msg2\x03"
        fake_run_git = mock.Mock(return_value=output)
        result = read_commits_in_range("old..new", run_git=fake_run_git)
        self.assertEqual(result, [("sha1", "msg1"), ("sha2", "msg2")])

    def test_empty_output_returns_empty_list(self):
        fake_run_git = mock.Mock(return_value="")
        self.assertEqual(read_commits_in_range("old..new", run_git=fake_run_git), [])


class ReadCommitMeasurement(unittest.TestCase):
    def test_measures_a_commit_with_a_parent(self):
        calls = []

        def fake_run_git(argv):
            calls.append(argv)
            if argv[0] == "rev-parse":
                return "parentsha\n"
            return "1\t2\ta.py\0"

        result = read_commit_measurement("mysha", run_git=fake_run_git)
        self.assertEqual(result, {"sha": "mysha", "files": 1, "lines": 3, "paths": ["a.py"]})
        self.assertEqual(calls[0], ["rev-parse", "mysha^"])
        self.assertEqual(
            calls[1],
            ["diff", "--numstat", "-z", "--no-renames", "-w", "--ignore-blank-lines", "parentsha", "mysha"],
        )

    def test_measures_a_root_commit_against_the_empty_tree(self):
        def fake_run_git(argv):
            if argv[0] == "rev-parse":
                raise QuickLaneError("no parent")
            if argv[0] == "hash-object":
                return "emptytreesha\n"
            return "1\t1\troot.py\0"

        result = read_commit_measurement("rootsha", run_git=fake_run_git)
        self.assertEqual(result["files"], 1)
        self.assertEqual(result["lines"], 2)

    def test_binary_file_counts_as_a_file_with_zero_lines(self):
        def fake_run_git(argv):
            if argv[0] == "rev-parse":
                return "parentsha\n"
            return "-\t-\timage.png\0"

        result = read_commit_measurement("mysha", run_git=fake_run_git)
        self.assertEqual(result, {"sha": "mysha", "files": 1, "lines": 0, "paths": ["image.png"]})


class RunGit(unittest.TestCase):
    def test_a_git_failure_raises_this_checks_own_error(self):
        fake_result = mock.Mock(returncode=1, stdout="", stderr="bad")
        with mock.patch("subprocess.run", return_value=fake_result):
            with self.assertRaises(QuickLaneError):
                run_git(["status"])


if __name__ == "__main__":
    unittest.main()
