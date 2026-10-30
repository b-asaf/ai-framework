import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from execution.verification import git_runner  # noqa: E402


class Other(Exception):
    pass


def finished(returncode=0, stdout="", stderr=""):
    return mock.Mock(returncode=returncode, stdout=stdout, stderr=stderr)


class RunGit(unittest.TestCase):
    def test_it_returns_stdout_and_starts_git_the_way_the_checks_need(self):
        with mock.patch("subprocess.run", return_value=finished(stdout="hello\n")) as mocked:
            self.assertEqual(git_runner.run_git(["status"]), "hello\n")
        mocked.assert_called_once_with(
            ["git", "status"], cwd=None, capture_output=True, encoding="utf-8", errors="replace",
            stdin=subprocess.DEVNULL, check=False,
        )

    def test_the_working_directory_is_forwarded(self):
        with mock.patch("subprocess.run", return_value=finished()) as mocked:
            git_runner.run_git(["status"], cwd="/some/dir")
        self.assertEqual(mocked.call_args.kwargs["cwd"], "/some/dir")

    def test_a_failing_git_raises_the_given_error_with_the_arguments_and_stderr(self):
        with mock.patch("subprocess.run", return_value=finished(1, stderr="bad")):
            with self.assertRaisesRegex(Other, r"\['log'\] failed: bad"):
                git_runner.run_git(["log"], error=Other)

    def test_a_git_that_cannot_start_raises_the_given_error(self):
        with mock.patch("subprocess.run", side_effect=OSError("missing")):
            with self.assertRaisesRegex(Other, "failed to run git"):
                git_runner.run_git(["log"], error=Other)

    def test_real_git_runs(self):
        self.assertTrue(git_runner.run_git(["--version"]).startswith("git version"))

    def test_real_git_failure_raises_git_error_by_default(self):
        with self.assertRaises(git_runner.GitError):
            git_runner.run_git(["no-such-subcommand"])


if __name__ == "__main__":
    unittest.main()
