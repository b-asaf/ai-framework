"""Tests for scripts/git-context.py."""
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest

SCRIPT = pathlib.Path(__file__).resolve().parent.parent / "scripts" / "git-context.py"


def run_script(cwd, env=None):
    return subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def init_repo(path, branch):
    subprocess.run(
        ["git", "init", "-q", "-b", branch],
        cwd=path,
        check=True,
        capture_output=True,
    )


class GitContextTest(unittest.TestCase):
    def test_prints_both_sections_and_branch(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            init_repo(tmp, "main")
            proc = run_script(tmp)
        self.assertEqual(proc.returncode, 0)
        lines = proc.stdout.splitlines()
        self.assertIn("--- status ---", lines)
        self.assertEqual(lines[-2:], ["--- branch ---", "main"])

    def test_reports_a_non_base_branch(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            init_repo(tmp, "fix/demo")
            proc = run_script(tmp)
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(proc.stdout.splitlines()[-1], "fix/demo")

    def test_outside_a_repo_fails_closed(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            env = dict(os.environ)
            env["GIT_CEILING_DIRECTORIES"] = str(pathlib.Path(tmp).parent)
            proc = run_script(tmp, env=env)
        self.assertEqual(proc.returncode, 1)
        self.assertIn("STATUS: ERROR", proc.stdout)


if __name__ == "__main__":
    unittest.main()
