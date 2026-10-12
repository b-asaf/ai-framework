import os
import subprocess
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tools"))

import validate_framework  # noqa: E402
from validate_framework import Agent  # noqa: E402

CATALOG = "docs/decisions/MODEL-ASSIGNMENT-MATRIX.md"


def make_agent(name, bash):
    return Agent(
        path=Path("agents") / (name + ".md"),
        mode=None,
        model=None,
        permission={"bash": bash},
        task_permissions={},
    )


def complete_bash():
    bash = {"*": "ask", "git commit *": "allow", "git branch *": "allow"}
    for rule in validate_framework.COMMIT_AGENT_DENIES:
        bash[rule] = "deny"
    return bash


class CommitAgentRule(unittest.TestCase):
    def test_complete_block_passes(self):
        self.assertEqual(validate_framework.lint_commit_agents(make_agent("committer", complete_bash())), [])

    def test_agent_that_cannot_commit_is_ignored(self):
        bash = {"*": "deny", "git status": "allow"}
        self.assertEqual(validate_framework.lint_commit_agents(make_agent("reviewer", bash)), [])

    def test_missing_deny_is_flagged(self):
        bash = complete_bash()
        del bash["gh pr ready*"]
        issues = validate_framework.lint_commit_agents(make_agent("committer", bash))
        self.assertEqual(len(issues), 1)
        self.assertIn("gh pr ready*", str(issues[0]))
        self.assertIn("<missing>", str(issues[0]))

    def test_allow_instead_of_deny_is_flagged(self):
        bash = complete_bash()
        bash["git push*"] = "allow"
        issues = validate_framework.lint_commit_agents(make_agent("committer", bash))
        self.assertEqual(len(issues), 1)
        self.assertIn("found allow", str(issues[0]))

    def test_deny_before_the_allow_is_flagged(self):
        bash = {"*": "ask", "git commit*--no-verify*": "deny", "git commit *": "allow", "git branch *": "allow"}
        for rule in validate_framework.COMMIT_AGENT_DENIES:
            bash.setdefault(rule, "deny")
        issues = validate_framework.lint_commit_agents(make_agent("committer", bash))
        self.assertEqual(len(issues), 1)
        self.assertIn("comes before an allow", str(issues[0]))
        self.assertIn("--no-verify", str(issues[0]))


class ValidatorFixtures(unittest.TestCase):
    def run_validator(self, fixture):
        env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
        return subprocess.run(
            [sys.executable, str(REPO / "tools" / "validate_framework.py"),
             "tests/fixtures/" + fixture, CATALOG],
            cwd=REPO, env=env, capture_output=True,
            encoding="utf-8", errors="replace",
        )

    def test_incomplete_committer_fails(self):
        result = self.run_validator("commit-agent-bad")
        output = result.stdout + result.stderr
        self.assertEqual(result.returncode, 1, output)
        self.assertIn("[commit-agent] committer", output)

    def test_complete_committer_passes_this_check(self):
        result = self.run_validator("commit-agent-ok")
        self.assertNotIn("[commit-agent]", result.stdout + result.stderr)


class RealOrchestrator(unittest.TestCase):
    def test_the_orchestrator_carries_every_deny(self):
        agent = validate_framework.load_agent(REPO / "agents" / "orchestrator.md")
        self.assertEqual(validate_framework.lint_commit_agents(agent), [])


if __name__ == "__main__":
    unittest.main()
