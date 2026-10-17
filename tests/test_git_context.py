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


def commit(path, message):
    subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@example.com", "-c", "commit.gpgsign=false",
         "commit", "--allow-empty", "--no-verify", "-q", "-m", message],
        cwd=path, check=True, capture_output=True,
    )


def checkout_new(path, branch):
    subprocess.run(["git", "checkout", "-q", "-b", branch], cwd=path, check=True, capture_output=True)


class AheadOfBaseTest(unittest.TestCase):
    def run_in(self, setup):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            init_repo(tmp, "main")
            setup(tmp)
            return run_script(tmp)

    def test_base_branch_is_zero_ahead(self):
        proc = self.run_in(lambda p: commit(p, "base"))
        self.assertEqual(proc.returncode, 0)
        self.assertIn("AHEAD_OF_BASE: 0", proc.stdout.splitlines())
        self.assertIn("BASE: main", proc.stdout.splitlines())

    def test_fresh_branch_is_zero_ahead(self):
        def setup(p):
            commit(p, "base")
            checkout_new(p, "fix/x")
        proc = self.run_in(setup)
        self.assertIn("AHEAD_OF_BASE: 0", proc.stdout.splitlines())

    def test_branch_with_commits_lists_them(self):
        def setup(p):
            commit(p, "base")
            checkout_new(p, "fix/x")
            commit(p, "first change")
            commit(p, "second change")
        proc = self.run_in(setup)
        lines = proc.stdout.splitlines()
        self.assertIn("AHEAD_OF_BASE: 2", lines)
        commits = [line for line in lines if line.startswith("COMMIT: ")]
        self.assertEqual(len(commits), 2)
        self.assertTrue(commits[0].endswith("second change"))

    def test_no_base_branch_is_unknown(self):
        proc = self.run_in(lambda p: None)
        self.assertEqual(proc.returncode, 0)
        self.assertIn("AHEAD_OF_BASE: unknown", proc.stdout.splitlines())

    def test_ahead_section_sits_between_status_and_branch(self):
        proc = self.run_in(lambda p: commit(p, "base"))
        lines = proc.stdout.splitlines()
        self.assertLess(lines.index("--- status ---"), lines.index("--- ahead ---"))
        self.assertLess(lines.index("--- ahead ---"), lines.index("--- branch ---"))


class OrchestratorContractTest(unittest.TestCase):
    def orchestrator_text(self):
        return (SCRIPT.parent.parent / "agents" / "orchestrator.md").read_text(encoding="utf-8")

    def test_orchestrator_reads_the_ahead_count(self):
        self.assertIn("AHEAD_OF_BASE", self.orchestrator_text())

    def test_quick_lane_does_not_offer_a_split(self):
        self.assertNotIn("or a split", self.orchestrator_text())


class AgentsMdBranchGuardTest(unittest.TestCase):
    def agents_md(self):
        raw = (SCRIPT.parent.parent / "AGENTS.md").read_text(encoding="utf-8")
        return " ".join(raw.replace(">", " ").split())

    def test_check_2_uses_the_ahead_count(self):
        text = self.agents_md()
        self.assertIn("AHEAD_OF_BASE", text)
        self.assertIn("Staying puts this task into the same PR", text)

    def test_check_2_recommends_a_new_branch_from_base(self):
        self.assertIn("(recommended)", self.agents_md())

    def test_implementation_agents_never_ask_the_branch_question(self):
        self.assertIn("Implementation agents never ask this question", self.agents_md())


if __name__ == "__main__":
    unittest.main()
