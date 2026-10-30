"""The verification checks against real git.

The other tests use a fake git runner, so the argument lists and the parsing of git's output are only
proven here. One repository is built once and read by every test.
"""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from execution.verification import git_runner  # noqa: E402
from execution.verification.checks import branch_protection as bp  # noqa: E402
from execution.verification.checks import dependency_change as dc  # noqa: E402

IDENTITY = ["-c", "user.name=Test", "-c", "user.email=test@example.com", "-c", "commit.gpgsign=false"]
TRAILER_MESSAGE = "feat: add caf\u00e9 dependency\n\nDependency-Approved: ana\n"


def git(folder, *args, check=True):
    return subprocess.run(["git", "-C", str(folder), *IDENTITY, *args], check=check, capture_output=True)


def make_repo(folder):
    subprocess.run(["git", "init", "-q", "-b", "main", "--template=", str(folder)], check=True, capture_output=True)


def write(folder, name, text):
    path = Path(folder) / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def head(folder):
    return git(folder, "rev-parse", "HEAD").stdout.decode("ascii").strip()


def commit(folder, scratch, files, message):
    for name, text in files.items():
        write(folder, name, text)
    note = Path(scratch) / "message.txt"
    note.write_text(message, encoding="utf-8", newline="\n")
    git(folder, "add", ".")
    git(folder, "commit", "-q", "--no-verify", "-F", str(note))
    return head(folder)


class RealGit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        repo_dir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        scratch_dir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        cls.addClassCleanup(repo_dir.cleanup)
        cls.addClassCleanup(scratch_dir.cleanup)
        repo, scratch = Path(repo_dir.name), scratch_dir.name
        make_repo(repo)
        cls.a = commit(repo, scratch, {"README.md": "one\n"}, "chore: init\n")
        cls.b = commit(repo, scratch, {"package.json": "{}\n", "docs/my file.txt": "x\n"}, TRAILER_MESSAGE)
        cls.c = commit(repo, scratch, {"package.json": '{"a": 1}\n'}, "chore: bump\n")
        git(repo, "update-ref", "refs/remotes/origin/main", cls.c)
        git(repo, "symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/main")
        git(repo, "checkout", "-q", "-b", "feature", cls.a)
        cls.d = commit(repo, scratch, {"requirements-dev.txt": "pytest\n"}, "feat: dev deps\n")
        git(repo, "checkout", "-q", "main")
        cls.repo = repo

    def dc_git(self, argv):
        return dc.run_git(argv, cwd=self.repo)

    def bp_git(self, argv):
        return bp.run_git(argv, cwd=self.repo)

    def paths(self, old, new, base=None):
        return dc.read_changed_paths(old, new, base, run_git=self.dc_git)

    def messages(self, old, new, base=None):
        return dc.read_commit_messages(old, new, base, run_git=self.dc_git)

    def test_a_normal_push_lists_every_changed_path_even_with_a_space(self):
        self.assertEqual(sorted(self.paths(self.a, self.b)), ["docs/my file.txt", "package.json"])

    def test_the_trailer_in_a_message_with_non_ascii_text_is_found(self):
        messages = self.messages(self.a, self.b)
        self.assertEqual(len(messages), 1)
        self.assertIn("caf\u00e9", messages[0])
        self.assertEqual(dc.find_violations(self.paths(self.a, self.b), messages), [])

    def test_a_manifest_change_without_the_trailer_is_a_violation(self):
        paths, messages = self.paths(self.b, self.c), self.messages(self.b, self.c)
        self.assertEqual(paths, ["package.json"])
        self.assertEqual(len(messages), 1)
        violations = dc.find_violations(paths, messages)
        self.assertEqual([item["manifests"] for item in violations], [["package.json"]])

    def test_the_trailer_on_any_commit_of_the_push_is_enough(self):
        messages = self.messages(self.a, self.c)
        self.assertEqual(len(messages), 2)
        self.assertEqual(dc.find_violations(self.paths(self.a, self.c), messages), [])

    def test_a_new_branch_is_compared_with_its_merge_base(self):
        paths = self.paths(dc._ZERO_SHA, self.d, "main")
        self.assertEqual(paths, ["requirements-dev.txt"])
        violations = dc.find_violations(paths, self.messages(dc._ZERO_SHA, self.d, "main"))
        self.assertEqual([item["manifests"] for item in violations], [["requirements-dev.txt"]])

    def test_a_new_branch_without_a_resolvable_protected_branch_fails_closed(self):
        with self.assertRaises(dc.DependencyChangeError):
            self.paths(dc._ZERO_SHA, self.d, "no-such-branch")

    def test_origin_head_is_read_from_real_git(self):
        self.assertEqual(bp.read_protected_branches(None, run_git=self.bp_git), ["main"])

    def test_without_origin_head_the_configured_branches_are_used_or_the_check_fails_closed(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as folder:
            make_repo(folder)

            def run(argv):
                return bp.run_git(argv, cwd=folder)

            config = {"protectedBranches": ["release/*"]}
            self.assertEqual(bp.read_protected_branches(config, run_git=run), ["release/*"])
            with self.assertRaises(bp.BranchProtectionError):
                bp.read_protected_branches(None, run_git=run)

    def test_a_failing_git_command_raises_each_checks_own_error(self):
        with self.assertRaises(dc.DependencyChangeError):
            dc.run_git(["no-such-subcommand"], cwd=self.repo)
        with self.assertRaises(bp.BranchProtectionError):
            bp.run_git(["no-such-subcommand"], cwd=self.repo)

    def test_the_shared_helper_decodes_utf8(self):
        out = git_runner.run_git(["log", "-1", "--format=%s", self.b], cwd=self.repo)
        self.assertEqual(out.strip(), "feat: add caf\u00e9 dependency")

    def test_a_commit_message_that_is_not_utf8_does_not_crash_the_check(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as folder:
            with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as scratch:
                make_repo(folder)
                write(folder, "a.txt", "x\n")
                git(folder, "add", ".")
                note = Path(scratch) / "m.txt"
                note.write_bytes(b"fix: caf\xe9\n")
                done = git(folder, "commit", "-q", "--no-verify", "-F", str(note), check=False)
                if done.returncode != 0:
                    self.skipTest("this git refuses a commit message that is not UTF-8")
                out = git_runner.run_git(["log", "-1", "--format=%B", head(folder)], cwd=folder)
        self.assertIn("caf", out)


if __name__ == "__main__":
    unittest.main()
