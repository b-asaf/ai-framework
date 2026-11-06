"""The pre-push gate edge script (execution/verification/run.py).

Unit tests drive `main` with fake stdin/env/run_git, following the style of
the other verification tests. The RealGit test class builds one real
temporary repository (like tests/test_verification_git.py) and exercises
run.py end to end, including one real subprocess invocation to prove the
`__main__` sys.path bootstrap works standalone (plan step 3A.2).
"""

import json
import subprocess
import sys
import tempfile
import unittest
from io import StringIO
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from execution.verification import run  # noqa: E402
from execution.verification.checks import branch_protection as bp  # noqa: E402
from execution.verification.checks import dependency_change as dc  # noqa: E402
from execution.verification.checks import quick_lane as ql  # noqa: E402

IDENTITY = ["-c", "user.name=Test", "-c", "user.email=test@example.com", "-c", "commit.gpgsign=false"]
ZERO = "0" * 40


def git(folder, *args, check=True):
    return subprocess.run(["git", "-C", str(folder), *IDENTITY, *args], check=check, capture_output=True)


def make_repo(folder):
    subprocess.run(["git", "init", "-q", "-b", "main", "--template=", str(folder)], check=True, capture_output=True)


def write(folder, name, text):
    path = Path(folder) / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def head(folder, ref="HEAD"):
    return git(folder, "rev-parse", ref).stdout.decode("ascii").strip()


def commit(folder, scratch, files, message):
    for name, text in files.items():
        write(folder, name, text)
    note = Path(scratch) / "message.txt"
    note.write_text(message, encoding="utf-8", newline="\n")
    git(folder, "add", ".")
    git(folder, "commit", "-q", "--no-verify", "-F", str(note))
    return head(folder)


class FakeRunGitUnit(unittest.TestCase):
    """Drive main() with a scripted fake run_git, no real git process."""

    def test_clean_push_is_not_blocked(self):
        stdin_text = "refs/heads/feature/x aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa refs/heads/feature/x dddddddddddddddddddddddddddddddddddddddd\n"

        def fake_run_git(argv, cwd=None, *, error):
            if argv[:2] == ["symbolic-ref", "--short"]:
                return "origin/main\n"
            if argv[0] == "merge-base":
                return "b" * 40 + "\n"
            if argv[0] == "diff":
                return ""
            if argv[0] == "log":
                return ""
            raise AssertionError(f"unexpected git call: {argv}")

        out = StringIO()
        with mock.patch("sys.stdout", out):
            code = run.main(
                ["run.py", "."], stdin_text,
                {"SKIP_VERIFICATION": ""},
                fake_run_git,
            )
        self.assertEqual(code, 0)
        self.assertEqual(out.getvalue(), "")

    def test_a_big_branch_is_blocked_with_a_fake_git(self):
        stdin_text = "refs/heads/feature/x " + "a" * 40 + " refs/heads/feature/x " + "d" * 40 + "\n"
        big = "diff --git a/x.js b/x.js\n--- a/x.js\n+++ b/x.js\n@@ -1,0 +1,2 @@\n+one\n+two\n"

        def fake_run_git(argv, cwd=None, *, error):
            if argv[0] == "symbolic-ref":
                return "origin/main\n"
            if argv[0] == "merge-base":
                return "b" * 40 + "\n"
            if argv[0] == "diff":
                return big if "-U0" in argv else ""
            if argv[0] == "log":
                return ""
            raise AssertionError(f"unexpected git call: {argv}")

        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / ".ai-framework.json").write_text('{"maxDiffLines": 1}', encoding="utf-8")
            out = StringIO()
            with mock.patch("sys.stdout", out):
                code = run.main(["run.py", tmp], stdin_text, {}, fake_run_git)
        self.assertEqual(code, 1)
        self.assertIn("BLOCKED diff_size", out.getvalue())
        self.assertIn("2 meaningful lines against origin/main", out.getvalue())

    def test_push_input_parse_failure_blocks_every_relevant_check(self):
        out = StringIO()
        with mock.patch("sys.stdout", out):
            code = run.main(["run.py", "."], "bad record here\n", {}, lambda *a, **k: "")
        self.assertEqual(code, 1)
        text = out.getvalue()
        self.assertIn("BLOCKED branch_protection", text)
        self.assertIn("BLOCKED dependency_change", text)
        self.assertIn("BLOCKED quick_lane", text)

    def test_skip_verification_does_not_block_on_dependency_or_quick_lane_parse_failure(self):
        out = StringIO()
        with mock.patch("sys.stdout", out):
            code = run.main(["run.py", "."], "bad record here\n", {"SKIP_VERIFICATION": "1"}, lambda *a, **k: "")
        self.assertEqual(code, 1)
        text = out.getvalue()
        self.assertIn("BLOCKED branch_protection", text)
        self.assertNotIn("BLOCKED dependency_change", text)
        self.assertNotIn("BLOCKED quick_lane", text)

    def test_malformed_config_is_a_violation(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / ".ai-framework.json").write_text("not json", encoding="utf-8")
            out = StringIO()
            with mock.patch("sys.stdout", out):
                code = run.main(["run.py", tmp], "", {}, lambda *a, **k: "")
            self.assertEqual(code, 1)
            self.assertIn("BLOCKED config", out.getvalue())

    def test_config_not_an_object_is_a_violation(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / ".ai-framework.json").write_text("[1, 2]", encoding="utf-8")
            out = StringIO()
            with mock.patch("sys.stdout", out):
                code = run.main(["run.py", tmp], "", {}, lambda *a, **k: "")
            self.assertEqual(code, 1)
            self.assertIn("BLOCKED config", out.getvalue())

    def test_missing_config_is_not_a_violation(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = StringIO()
            fake_run_git = lambda argv, cwd=None, *, error: "origin/main\n"
            with mock.patch("sys.stdout", out):
                code = run.main(["run.py", tmp], "", {}, fake_run_git)
            self.assertEqual(code, 0)
            self.assertEqual(out.getvalue(), "")

    def test_empty_stdin_is_a_clean_push(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = StringIO()
            fake_run_git = lambda argv, cwd=None, *, error: "origin/main\n"
            with mock.patch("sys.stdout", out):
                code = run.main(["run.py", tmp], "", {}, fake_run_git)
            self.assertEqual(code, 0)


class RealGit(unittest.TestCase):
    """Real temporary git repository, like tests/test_verification_git.py."""

    @classmethod
    def setUpClass(cls):
        repo_dir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        scratch_dir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        cls.addClassCleanup(repo_dir.cleanup)
        cls.addClassCleanup(scratch_dir.cleanup)
        repo, scratch = Path(repo_dir.name), scratch_dir.name
        make_repo(repo)
        cls.a = commit(repo, scratch, {"README.md": "one\n"}, "chore: init\n")
        git(repo, "update-ref", "refs/remotes/origin/main", cls.a)
        git(repo, "symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/main")
        cls.repo = repo
        cls.scratch = scratch

    def run_git(self, argv, cwd=None, *, error):
        from execution.verification.git_runner import run_git as shared_run_git

        return shared_run_git(argv, cwd=cwd or self.repo, error=error)

    def main(self, stdin_text, env=None):
        out = StringIO()
        with mock.patch("sys.stdout", out):
            code = run.main(["run.py", str(self.repo)], stdin_text, env or {}, self.run_git)
        return code, out.getvalue()

    def test_push_to_protected_branch_is_blocked(self):
        code, out = self.main(f"refs/heads/main {self.a} refs/heads/main {self.a}\n")
        self.assertEqual(code, 1)
        self.assertIn("BLOCKED branch_protection", out)

    def test_push_to_a_feature_branch_is_not_blocked(self):
        b = commit(self.repo, self.scratch, {"docs/x.txt": "x\n"}, "feat: thing\n")
        git(self.repo, "branch", "feature/a", b)
        code, out = self.main(f"refs/heads/feature/a {b} refs/heads/feature/a {ZERO}\n")
        self.assertEqual(code, 0)
        self.assertEqual(out, "")

    def test_a_new_branch_is_compared_with_its_merge_base(self):
        git(self.repo, "checkout", "-q", "-b", "feature/newbranch", self.a)
        new_head = commit(self.repo, self.scratch, {"docs/y.txt": "y\n"}, "feat: small change\n")
        git(self.repo, "checkout", "-q", "main")
        code, out = self.main(f"refs/heads/feature/newbranch {new_head} refs/heads/feature/newbranch {ZERO}\n")
        self.assertEqual(code, 0)

    def test_manifest_change_with_trailer_is_not_blocked(self):
        git(self.repo, "checkout", "-q", "-b", "feature/dep-ok", self.a)
        dep_head = commit(
            self.repo, self.scratch, {"package.json": "{}\n"}, "chore: dep\n\nDependency-Approved: me\n"
        )
        git(self.repo, "checkout", "-q", "main")
        code, out = self.main(f"refs/heads/feature/dep-ok {dep_head} refs/heads/feature/dep-ok {ZERO}\n")
        self.assertEqual(code, 0)

    def test_manifest_change_without_trailer_is_blocked(self):
        git(self.repo, "checkout", "-q", "-b", "feature/dep-bad", self.a)
        dep_head = commit(self.repo, self.scratch, {"package.json": "{}\n"}, "chore: dep\n")
        git(self.repo, "checkout", "-q", "main")
        code, out = self.main(f"refs/heads/feature/dep-bad {dep_head} refs/heads/feature/dep-bad {ZERO}\n")
        self.assertEqual(code, 1)
        self.assertIn("BLOCKED dependency_change", out)

    def test_quick_lane_commit_within_limits_is_not_blocked(self):
        git(self.repo, "checkout", "-q", "-b", "feature/quick-ok", self.a)
        quick_head = commit(
            self.repo, self.scratch, {"docs/z.txt": "z\n"}, "fix: small\n\nLane: quick\n"
        )
        git(self.repo, "checkout", "-q", "main")
        code, out = self.main(f"refs/heads/feature/quick-ok {quick_head} refs/heads/feature/quick-ok {ZERO}\n")
        self.assertEqual(code, 0)

    def test_quick_lane_commit_over_limits_is_blocked(self):
        git(self.repo, "checkout", "-q", "-b", "feature/quick-over", self.a)
        quick_head = commit(
            self.repo, self.scratch,
            {"b.txt": "1\n", "c.txt": "1\n", "d.txt": "1\n", "e.txt": "1\n"},
            "fix: too much\n\nLane: quick\n",
        )
        git(self.repo, "checkout", "-q", "main")
        code, out = self.main(f"refs/heads/feature/quick-over {quick_head} refs/heads/feature/quick-over {ZERO}\n")
        self.assertEqual(code, 1)
        self.assertIn("BLOCKED quick_lane", out)

    def test_quick_lane_commit_touching_a_manifest_is_blocked(self):
        git(self.repo, "checkout", "-q", "-b", "feature/quick-manifest", self.a)
        quick_head = commit(
            self.repo, self.scratch, {"package.json": "{}\n"}, "fix: dep\n\nLane: quick\n"
        )
        git(self.repo, "checkout", "-q", "main")
        code, out = self.main(
            f"refs/heads/feature/quick-manifest {quick_head} refs/heads/feature/quick-manifest {ZERO}\n"
        )
        self.assertEqual(code, 1)
        self.assertIn("BLOCKED quick_lane", out)

    def test_missing_ai_framework_json_is_not_a_violation(self):
        self.assertFalse((self.repo / ".ai-framework.json").exists())
        code, out = self.main(f"refs/heads/main {self.a} refs/heads/main {ZERO}\n")
        # deletion of a protected branch is still blocked by branch_protection,
        # but config itself is not the reason, so no "BLOCKED config" line.
        self.assertNotIn("BLOCKED config", out)

    def test_malformed_ai_framework_json_fails_closed(self):
        config_path = self.repo / ".ai-framework.json"
        config_path.write_text("not json {", encoding="utf-8")
        try:
            code, out = self.main(f"refs/heads/feature/doesnotmatter {self.a} refs/heads/feature/doesnotmatter {ZERO}\n")
            self.assertEqual(code, 1)
            self.assertIn("BLOCKED config", out)
        finally:
            config_path.unlink()

    def test_no_origin_head_and_no_protected_branches_fails_closed(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as folder:
            with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as scratch:
                make_repo(folder)
                a = commit(folder, scratch, {"x.txt": "x\n"}, "chore: init\n")

                def local_run_git(argv, cwd=None, *, error):
                    from execution.verification.git_runner import run_git as shared_run_git

                    return shared_run_git(argv, cwd=cwd or folder, error=error)

                out = StringIO()
                with mock.patch("sys.stdout", out):
                    code = run.main(
                        ["run.py", folder], f"refs/heads/feature/x {a} refs/heads/feature/x {ZERO}\n",
                        {}, local_run_git,
                    )
                self.assertEqual(code, 1)
                self.assertIn("BLOCKED branch_protection", out.getvalue())

    def test_skip_verification_skips_dependency_change_and_quick_lane_but_not_branch_protection(self):
        code, out = self.main(
            f"refs/heads/main {self.a} refs/heads/main {self.a}\n", env={"SKIP_VERIFICATION": "1"}
        )
        self.assertEqual(code, 1)
        self.assertIn("SKIP_VERIFICATION=1", out)
        self.assertIn("BLOCKED branch_protection", out)

    def test_a_tag_push_is_ignored(self):
        code, out = self.main(f"refs/tags/v1.0 {self.a} refs/tags/v1.0 {ZERO}\n")
        self.assertEqual(code, 0)
        self.assertEqual(out, "")

    def test_a_branch_deletion_has_no_commits_and_is_not_a_violation(self):
        git(self.repo, "checkout", "-q", "-b", "feature/to-delete", self.a)
        delete_head = commit(self.repo, self.scratch, {"docs/w.txt": "w\n"}, "feat: thing\n")
        git(self.repo, "checkout", "-q", "main")
        code, out = self.main(f"(delete) {ZERO} refs/heads/feature/to-delete {delete_head}\n")
        self.assertEqual(code, 0)


class RunPyAsSubprocess(unittest.TestCase):
    """Proves the __main__ sys.path bootstrap works standalone (plan step 3A.2)."""

    def test_running_the_script_directly_works(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as folder:
            with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as scratch:
                make_repo(folder)
                a = commit(folder, scratch, {"x.txt": "x\n"}, "chore: init\n")
                git(folder, "update-ref", "refs/remotes/origin/main", a)
                git(folder, "symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/main")

                script = REPO / "execution" / "verification" / "run.py"
                stdin_text = f"refs/heads/main {a} refs/heads/main {a}\n"
                result = subprocess.run(
                    [sys.executable, str(script), str(folder)],
                    input=stdin_text, capture_output=True, text=True, cwd=folder,
                )
                self.assertEqual(result.returncode, 1)
                self.assertIn("BLOCKED branch_protection", result.stdout)


if __name__ == "__main__":
    unittest.main()
