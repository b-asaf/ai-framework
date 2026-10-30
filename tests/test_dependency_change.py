import sys
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from execution.verification.checks.dependency_change import (  # noqa: E402
    DependencyChangeError,
    _ZERO_SHA,
    find_violations,
    read_changed_paths,
    read_commit_messages,
    run_git,
)


def failing_runner(*args, **kwargs):
    raise AssertionError("run_git should not have been called")


class FindViolations(unittest.TestCase):
    def test_non_manifest_file_no_trailer(self):
        self.assertEqual(find_violations(["src/app.py"], ["fix: bug"]), [])

    def test_manifest_changed_no_trailer_is_violation(self):
        violations = find_violations(["package.json"], ["fix: bug"])
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["reason"], "dependency_change_without_approval")
        self.assertEqual(violations[0]["manifests"], ["package.json"])

    def test_manifest_changed_with_trailer_is_clean(self):
        messages = ["fix: bug", "Dependency-Approved: someone"]
        self.assertEqual(find_violations(["package.json"], messages), [])

    def test_glob_match_build_gradle_variant(self):
        violations = find_violations(["build.gradle.kts"], ["fix: bug"])
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["manifests"], ["build.gradle.kts"])

    def test_near_miss_filename_does_not_match(self):
        self.assertEqual(
            find_violations(["my-package.json-notes.txt"], ["fix: bug"]), []
        )

    def test_multiple_manifests_sorted_in_violation(self):
        violations = find_violations(
            ["pyproject.toml", "package.json"], ["fix: bug"]
        )
        self.assertEqual(
            violations[0]["manifests"], ["package.json", "pyproject.toml"]
        )

    def test_trailer_on_later_line_of_multiline_message_detected(self):
        message = "Add dependency\n\nDependency-Approved: someone"
        self.assertEqual(find_violations(["package.json"], [message]), [])

    def test_trailer_in_only_one_of_several_messages_or_semantics(self):
        messages = ["unrelated commit", "Dependency-Approved: someone"]
        self.assertEqual(find_violations(["package.json"], messages), [])

    def test_wrong_case_trailer_not_detected(self):
        messages = ["dependency-approved: someone"]
        violations = find_violations(["package.json"], messages)
        self.assertEqual(len(violations), 1)

    def test_trailer_as_substring_mid_line_not_detected(self):
        messages = ["see Dependency-Approved: elsewhere in a sentence"]
        violations = find_violations(["package.json"], messages)
        self.assertEqual(len(violations), 1)

    def test_custom_trailer_parameter_respected(self):
        messages = ["Approved-By: someone"]
        self.assertEqual(
            find_violations(["package.json"], messages, trailer="Approved-By:"), []
        )
        violations = find_violations(["package.json"], messages, trailer="Other-Trailer:")
        self.assertEqual(len(violations), 1)


class ReadChangedPaths(unittest.TestCase):
    def test_normal_range_argv(self):
        fake_run_git = mock.Mock(return_value="a.txt\0b.txt\0")
        result = read_changed_paths("old123", "new456", run_git=fake_run_git)
        self.assertEqual(result, ["a.txt", "b.txt"])
        fake_run_git.assert_called_once_with(
            ["diff", "--name-only", "--no-renames", "-z", "old123..new456", "--"]
        )

    def test_empty_successful_diff_output(self):
        fake_run_git = mock.Mock(return_value="")
        result = read_changed_paths("old123", "new456", run_git=fake_run_git)
        self.assertEqual(result, [])

    def test_run_git_raising_raises(self):
        fake_run_git = mock.Mock(side_effect=DependencyChangeError("boom"))
        with self.assertRaises(DependencyChangeError):
            read_changed_paths("old123", "new456", run_git=fake_run_git)

    def test_new_sha_zero_returns_empty_and_run_git_never_called(self):
        result = read_changed_paths("old123", _ZERO_SHA, run_git=failing_runner)
        self.assertEqual(result, [])

    def test_new_branch_case_with_valid_protected_branch(self):
        calls = []

        def fake_run_git(argv):
            calls.append(argv)
            if argv[0] == "merge-base":
                return "mergebasesha\n"
            return "a.txt\0"

        result = read_changed_paths(
            _ZERO_SHA, "new456", "main", run_git=fake_run_git
        )
        self.assertEqual(result, ["a.txt"])
        self.assertEqual(calls[0], ["merge-base", "new456", "main"])
        self.assertEqual(
            calls[1],
            ["diff", "--name-only", "--no-renames", "-z", "mergebasesha..new456", "--"],
        )

    def test_new_branch_case_missing_protected_branch_raises(self):
        with self.assertRaises(DependencyChangeError):
            read_changed_paths(_ZERO_SHA, "new456", None, run_git=failing_runner)

    def test_new_branch_case_glob_protected_branch_raises(self):
        with self.assertRaises(DependencyChangeError):
            read_changed_paths(_ZERO_SHA, "new456", "release/*", run_git=failing_runner)

    def test_merge_base_failure_raises(self):
        fake_run_git = mock.Mock(side_effect=DependencyChangeError("no merge base"))
        with self.assertRaises(DependencyChangeError):
            read_changed_paths(_ZERO_SHA, "new456", "main", run_git=fake_run_git)

    def test_empty_old_sha_raises(self):
        with self.assertRaises(DependencyChangeError):
            read_changed_paths("", "new456", run_git=failing_runner)

    def test_none_old_sha_raises(self):
        with self.assertRaises(DependencyChangeError):
            read_changed_paths(None, "new456", run_git=failing_runner)

    def test_empty_new_sha_raises(self):
        with self.assertRaises(DependencyChangeError):
            read_changed_paths("old123", "", run_git=failing_runner)

    def test_none_new_sha_raises(self):
        with self.assertRaises(DependencyChangeError):
            read_changed_paths("old123", None, run_git=failing_runner)


class MergeBaseValidation(unittest.TestCase):
    def test_empty_merge_base_output_raises(self):
        fake_run_git = mock.Mock(return_value="")
        with self.assertRaises(DependencyChangeError):
            read_changed_paths(_ZERO_SHA, "new456", "main", run_git=fake_run_git)

    def test_whitespace_only_merge_base_output_raises(self):
        fake_run_git = mock.Mock(return_value="   \n")
        with self.assertRaises(DependencyChangeError):
            read_changed_paths(_ZERO_SHA, "new456", "main", run_git=fake_run_git)

    def test_multiline_merge_base_output_raises(self):
        fake_run_git = mock.Mock(return_value="abc123\ndef456\n")
        with self.assertRaises(DependencyChangeError):
            read_changed_paths(_ZERO_SHA, "new456", "main", run_git=fake_run_git)

    def test_merge_base_runner_raising_plain_exception_is_wrapped(self):
        def fake_run_git(argv):
            raise ValueError("unexpected failure")

        with self.assertRaises(DependencyChangeError):
            read_changed_paths(_ZERO_SHA, "new456", "main", run_git=fake_run_git)


    def test_normal_range_argv(self):
        fake_run_git = mock.Mock(return_value="msg1\0msg2\0")
        result = read_commit_messages("old123", "new456", run_git=fake_run_git)
        self.assertEqual(result, ["msg1", "msg2"])
        fake_run_git.assert_called_once_with(
            ["log", "--format=%B%x00", "old123..new456"]
        )

    def test_multiline_message_preserved_intact(self):
        fake_run_git = mock.Mock(return_value="line1\nline2\0")
        result = read_commit_messages("old123", "new456", run_git=fake_run_git)
        self.assertEqual(result, ["line1\nline2"])

    def test_multiple_messages_split_on_nul_no_phantom(self):
        fake_run_git = mock.Mock(return_value="msg1\0msg2\0msg3\0")
        result = read_commit_messages("old123", "new456", run_git=fake_run_git)
        self.assertEqual(result, ["msg1", "msg2", "msg3"])

    def test_empty_successful_log_output(self):
        fake_run_git = mock.Mock(return_value="")
        result = read_commit_messages("old123", "new456", run_git=fake_run_git)
        self.assertEqual(result, [])

    def test_run_git_raising_raises(self):
        fake_run_git = mock.Mock(side_effect=DependencyChangeError("boom"))
        with self.assertRaises(DependencyChangeError):
            read_commit_messages("old123", "new456", run_git=fake_run_git)

    def test_new_sha_zero_returns_empty_and_run_git_never_called(self):
        result = read_commit_messages("old123", _ZERO_SHA, run_git=failing_runner)
        self.assertEqual(result, [])

    def test_new_branch_case_with_valid_protected_branch(self):
        calls = []

        def fake_run_git(argv):
            calls.append(argv)
            if argv[0] == "merge-base":
                return "mergebasesha\n"
            return "msg1\0"

        result = read_commit_messages(
            _ZERO_SHA, "new456", "main", run_git=fake_run_git
        )
        self.assertEqual(result, ["msg1"])
        self.assertEqual(calls[0], ["merge-base", "new456", "main"])
        self.assertEqual(calls[1], ["log", "--format=%B%x00", "mergebasesha..new456"])

    def test_new_branch_case_missing_protected_branch_raises(self):
        with self.assertRaises(DependencyChangeError):
            read_commit_messages(_ZERO_SHA, "new456", None, run_git=failing_runner)

    def test_new_branch_case_glob_protected_branch_raises(self):
        with self.assertRaises(DependencyChangeError):
            read_commit_messages(_ZERO_SHA, "new456", "release/*", run_git=failing_runner)

    def test_merge_base_failure_raises(self):
        fake_run_git = mock.Mock(side_effect=DependencyChangeError("no merge base"))
        with self.assertRaises(DependencyChangeError):
            read_commit_messages(_ZERO_SHA, "new456", "main", run_git=fake_run_git)

    def test_empty_old_sha_raises(self):
        with self.assertRaises(DependencyChangeError):
            read_commit_messages("", "new456", run_git=failing_runner)

    def test_none_old_sha_raises(self):
        with self.assertRaises(DependencyChangeError):
            read_commit_messages(None, "new456", run_git=failing_runner)

    def test_empty_new_sha_raises(self):
        with self.assertRaises(DependencyChangeError):
            read_commit_messages("old123", "", run_git=failing_runner)

    def test_none_new_sha_raises(self):
        with self.assertRaises(DependencyChangeError):
            read_commit_messages("old123", None, run_git=failing_runner)


class RunGit(unittest.TestCase):
    def test_a_git_failure_raises_this_checks_own_error(self):
        fake_result = mock.Mock(returncode=1, stdout="", stderr="bad")
        with mock.patch("subprocess.run", return_value=fake_result):
            with self.assertRaises(DependencyChangeError):
                run_git(["status"])
        with mock.patch("subprocess.run", side_effect=OSError("missing")):
            with self.assertRaises(DependencyChangeError):
                run_git(["status"])

    def test_the_working_directory_is_forwarded(self):
        fake_result = mock.Mock(returncode=0, stdout="", stderr="")
        with mock.patch("subprocess.run", return_value=fake_result) as mocked:
            run_git(["status"], cwd="/some/dir")
        self.assertEqual(mocked.call_args.kwargs["cwd"], "/some/dir")


class CommitMessageOutputShape(unittest.TestCase):
    def test_the_newline_git_adds_after_the_last_terminator_is_not_a_message(self):
        output = "one\n\0\ntwo\n\0\n"
        messages = read_commit_messages("a" * 40, "b" * 40, run_git=lambda argv: output)
        self.assertEqual(messages, ["one\n", "\ntwo\n"])


class ManifestNames(unittest.TestCase):
    # The files the agents ask about before editing (agents/backend.md and agents/api.md).
    GUARDED = (
        "package.json", "package-lock.json", "yarn.lock", "pnpm-lock.yaml", "pom.xml",
        "build.gradle", "build.gradle.kts", "requirements.txt", "requirements-dev.txt",
        "pyproject.toml", "poetry.lock", "Pipfile", "Pipfile.lock",
    )

    def test_every_manifest_the_agents_guard_counts_as_a_manifest(self):
        for name in self.GUARDED:
            with self.subTest(name=name):
                self.assertEqual(len(find_violations([f"sub/{name}"], [])), 1)


if __name__ == "__main__":
    unittest.main()
