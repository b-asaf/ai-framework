import sys
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from execution.verification.checks.branch_protection import (  # noqa: E402
    BranchProtectionError,
    find_violations,
    read_protected_branches,
    read_pushed_branches,
    run_git,
)

PROTECTED = ["main", "release/*"]


class FindViolations(unittest.TestCase):
    def test_non_protected_branch_is_clean(self):
        self.assertEqual(find_violations(["feature/x"], PROTECTED), [])

    def test_exact_protected_name_is_violation(self):
        violations = find_violations(["main"], PROTECTED)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["branch"], "main")
        self.assertEqual(violations[0]["matched_pattern"], "main")
        self.assertEqual(violations[0]["reason"], "protected_branch_push")

    def test_glob_pattern_matches(self):
        violations = find_violations(["release/1.0"], PROTECTED)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["matched_pattern"], "release/*")

    def test_case_sensitivity(self):
        self.assertEqual(find_violations(["Main"], PROTECTED), [])

    def test_overlapping_patterns_report_first_match_once(self):
        patterns = ["release/*", "release/1.0"]
        violations = find_violations(["release/1.0"], patterns)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["matched_pattern"], "release/*")

    def test_multiple_branches_only_protected_appear_in_order(self):
        violations = find_violations(["feature/x", "main", "release/2.0"], PROTECTED)
        self.assertEqual([v["branch"] for v in violations], ["main", "release/2.0"])

    def test_empty_pushed_list(self):
        self.assertEqual(find_violations([], PROTECTED), [])


class ReadPushedBranches(unittest.TestCase):
    def test_multiple_valid_branch_records(self):
        text = (
            "refs/heads/main abc123 refs/heads/main def456\n"
            "refs/heads/feature/x 111 refs/heads/feature/x 222\n"
        )
        self.assertEqual(read_pushed_branches(text), ["main", "feature/x"])

    def test_empty_stdin(self):
        self.assertEqual(read_pushed_branches(""), [])

    def test_whitespace_only_stdin(self):
        self.assertEqual(read_pushed_branches("   \n  \n"), [])

    def test_tag_only_stdin(self):
        text = "refs/tags/v1.0 abc123 refs/tags/v1.0 def456\n"
        self.assertEqual(read_pushed_branches(text), [])

    def test_mixed_tag_and_branch_records(self):
        text = (
            "refs/tags/v1.0 abc123 refs/tags/v1.0 def456\n"
            "refs/heads/main 111 refs/heads/main 222\n"
        )
        self.assertEqual(read_pushed_branches(text), ["main"])

    def test_three_fields_raises(self):
        with self.assertRaises(BranchProtectionError):
            read_pushed_branches("refs/heads/main abc123 refs/heads/main\n")

    def test_five_fields_raises(self):
        with self.assertRaises(BranchProtectionError):
            read_pushed_branches("refs/heads/main abc123 refs/heads/main def456 extra\n")

    def test_malformed_record_mixed_with_valid_raises(self):
        text = (
            "refs/heads/main abc123 refs/heads/main def456\n"
            "bad record here\n"
        )
        with self.assertRaises(BranchProtectionError):
            read_pushed_branches(text)

    def test_interior_blank_line_raises(self):
        text = (
            "refs/heads/main abc123 refs/heads/main def456\n"
            "\n"
            "refs/heads/feature/x 111 refs/heads/feature/x 222\n"
        )
        with self.assertRaises(BranchProtectionError):
            read_pushed_branches(text)

    def test_single_trailing_newline_does_not_add_phantom_entry(self):
        text = "refs/heads/main abc123 refs/heads/main def456\n"
        self.assertEqual(read_pushed_branches(text), ["main"])

    def test_refs_heads_with_nothing_after_raises(self):
        text = "refs/heads/ abc123 refs/heads/ def456\n"
        with self.assertRaises(BranchProtectionError):
            read_pushed_branches(text)

    def test_deletion_zero_local_sha_still_returns_branch_and_is_a_violation(self):
        zero = "0" * 40
        text = f"(delete) {zero} refs/heads/main def456\n"
        branches = read_pushed_branches(text)
        self.assertEqual(branches, ["main"])
        violations = find_violations(branches, PROTECTED)
        self.assertEqual(len(violations), 1)


class ReadProtectedBranches(unittest.TestCase):
    def test_origin_head_resolves_no_config(self):
        fake_run_git = mock.Mock(return_value="origin/main\n")
        result = read_protected_branches(run_git=fake_run_git)
        self.assertEqual(result, ["main"])

    def test_origin_resolves_to_nested_branch(self):
        fake_run_git = mock.Mock(return_value="origin/release/1.0\n")
        result = read_protected_branches(run_git=fake_run_git)
        self.assertEqual(result, ["release/1.0"])

    def test_origin_and_config_both_contribute_no_duplicates(self):
        fake_run_git = mock.Mock(return_value="origin/main\n")
        config = {"protectedBranches": ["main", "release/*"]}
        result = read_protected_branches(config, run_git=fake_run_git)
        self.assertEqual(result, ["main", "release/*"])

    def test_origin_unavailable_valid_config_succeeds(self):
        fake_run_git = mock.Mock(side_effect=BranchProtectionError("no remote"))
        config = {"protectedBranches": ["main"]}
        result = read_protected_branches(config, run_git=fake_run_git)
        self.assertEqual(result, ["main"])

    def test_origin_unavailable_and_config_missing_raises(self):
        fake_run_git = mock.Mock(side_effect=BranchProtectionError("no remote"))
        with self.assertRaises(BranchProtectionError):
            read_protected_branches(run_git=fake_run_git)

    def test_origin_available_but_config_is_bare_string_raises(self):
        fake_run_git = mock.Mock(return_value="origin/main\n")
        config = {"protectedBranches": "main"}
        with self.assertRaises(BranchProtectionError):
            read_protected_branches(config, run_git=fake_run_git)

    def test_config_none_treated_as_empty_list(self):
        fake_run_git = mock.Mock(return_value="origin/main\n")
        result = read_protected_branches(None, run_git=fake_run_git)
        self.assertEqual(result, ["main"])

    def test_config_list_with_blank_entry_raises(self):
        fake_run_git = mock.Mock(return_value="origin/main\n")
        config = {"protectedBranches": ["main", "   "]}
        with self.assertRaises(BranchProtectionError):
            read_protected_branches(config, run_git=fake_run_git)

    def test_config_not_a_dict_raises(self):
        fake_run_git = mock.Mock(return_value="origin/main\n")
        with self.assertRaises(BranchProtectionError):
            read_protected_branches(["main"], run_git=fake_run_git)

    def test_run_git_passed_by_keyword(self):
        fake_run_git = mock.Mock(return_value="origin/main\n")
        result = read_protected_branches(config=None, run_git=fake_run_git)
        self.assertEqual(result, ["main"])

    def test_multiline_origin_output_treated_as_unavailable(self):
        fake_run_git = mock.Mock(return_value="origin/main\norigin/evil\n")
        config = {"protectedBranches": ["fallback"]}
        result = read_protected_branches(config, run_git=fake_run_git)
        self.assertEqual(result, ["fallback"])

    def test_multiline_origin_output_and_no_config_raises(self):
        fake_run_git = mock.Mock(return_value="origin/main\norigin/evil\n")
        with self.assertRaises(BranchProtectionError):
            read_protected_branches(run_git=fake_run_git)

    def test_origin_output_with_embedded_whitespace_treated_as_unavailable(self):
        fake_run_git = mock.Mock(return_value="origin/release 1.0\n")
        config = {"protectedBranches": ["fallback"]}
        result = read_protected_branches(config, run_git=fake_run_git)
        self.assertEqual(result, ["fallback"])


class RunGit(unittest.TestCase):
    def test_successful_call_returns_stdout_and_argv(self):
        fake_result = mock.Mock(returncode=0, stdout="hello\n", stderr="")
        with mock.patch("subprocess.run", return_value=fake_result) as mocked:
            output = run_git(["status"])
        self.assertEqual(output, "hello\n")
        mocked.assert_called_once_with(
            ["git", "status"], cwd=None, capture_output=True, text=True, check=False
        )

    def test_cwd_is_forwarded(self):
        fake_result = mock.Mock(returncode=0, stdout="", stderr="")
        with mock.patch("subprocess.run", return_value=fake_result) as mocked:
            run_git(["status"], cwd="/some/dir")
        mocked.assert_called_once_with(
            ["git", "status"], cwd="/some/dir", capture_output=True, text=True, check=False
        )

    def test_nonzero_exit_raises(self):
        fake_result = mock.Mock(returncode=1, stdout="", stderr="bad")
        with mock.patch("subprocess.run", return_value=fake_result):
            with self.assertRaises(BranchProtectionError):
                run_git(["status"])

    def test_oserror_raises(self):
        with mock.patch("subprocess.run", side_effect=OSError("missing")):
            with self.assertRaises(BranchProtectionError):
                run_git(["status"])


if __name__ == "__main__":
    unittest.main()
