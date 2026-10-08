import os
import subprocess
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tools"))

import validate_agents  # noqa: E402
from validate_agents import Agent  # noqa: E402

CATALOG = "docs/decisions/MODEL-ASSIGNMENT-MATRIX.md"
FIXTURES = REPO / "tests" / "fixtures"
LEAKY = FIXTURES / "read-only-leak" / "agents" / "leaky.md"
TIGHT = FIXTURES / "read-only-ok" / "agents" / "tight.md"


def make_agent(name, permission):
    return Agent(
        path=Path("agents") / (name + ".md"),
        mode=None,
        model=None,
        permission=permission,
        task_permissions={},
    )


class ReadOnlyRule(unittest.TestCase):
    def test_missing_task_deny_is_flagged(self):
        issues = validate_agents.lint_read_only(
            make_agent("reviewer", {"edit": "deny", "write": "deny"})
        )
        self.assertEqual(len(issues), 1)
        self.assertIn("task must be denied too", str(issues[0]))
        self.assertIn("<missing>", str(issues[0]))

    def test_write_allow_is_flagged(self):
        issues = validate_agents.lint_read_only(
            make_agent("reviewer", {"edit": "deny", "write": "allow", "task": "deny"})
        )
        self.assertEqual(len(issues), 1)
        self.assertIn("write must be denied too", str(issues[0]))

    def test_task_pattern_block_is_flagged(self):
        issues = validate_agents.lint_read_only(
            make_agent("reviewer", {"edit": "deny", "write": "deny", "task": {"general": "deny"}})
        )
        self.assertEqual(len(issues), 1)
        self.assertIn("<pattern block>", str(issues[0]))

    def test_fully_denied_passes(self):
        permission = {"edit": "deny", "write": "deny", "task": "deny"}
        self.assertEqual(validate_agents.lint_read_only(make_agent("reviewer", permission)), [])

    def test_agent_that_can_edit_is_ignored(self):
        permission = {"edit": {"*": "allow"}, "write": {"*": "allow"}}
        self.assertEqual(validate_agents.lint_read_only(make_agent("backend", permission)), [])

    def test_qa_may_write_but_still_needs_task_deny(self):
        open_task = make_agent("qa", {"edit": "deny", "write": "allow"})
        issues = validate_agents.lint_read_only(open_task)
        self.assertEqual(len(issues), 1)
        self.assertIn("task must be denied too", str(issues[0]))
        closed = make_agent("qa", {"edit": "deny", "write": "allow", "task": "deny"})
        self.assertEqual(validate_agents.lint_read_only(closed), [])

    def test_orchestrator_may_keep_its_task_block(self):
        permission = {"edit": "deny", "write": "deny", "task": {"general": "deny"}}
        self.assertEqual(validate_agents.lint_read_only(make_agent("orchestrator", permission)), [])

    def test_exemptions_do_not_leak_to_other_agents(self):
        permission = {"edit": "deny", "write": "allow", "task": "deny"}
        issues = validate_agents.lint_read_only(make_agent("other", permission))
        self.assertEqual(len(issues), 1)
        self.assertIn("write must be denied too", str(issues[0]))


class ReadOnlyFixtures(unittest.TestCase):
    def run_validator(self, fixture):
        env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
        return subprocess.run(
            [sys.executable, str(REPO / "tools" / "validate_agents.py"),
             "tests/fixtures/" + fixture, CATALOG],
            cwd=REPO, env=env, capture_output=True,
            encoding="utf-8", errors="replace",
        )

    def test_blanket_task_deny_is_understood(self):
        agent = validate_agents.load_agent(TIGHT)
        self.assertEqual(agent.task_permissions, {})
        self.assertEqual(agent.permission_value("task.general"), "deny")
        self.assertEqual(validate_agents.lint_read_only(agent), [])

    def test_leaky_fixture_is_flagged(self):
        issues = validate_agents.lint_read_only(validate_agents.load_agent(LEAKY))
        self.assertEqual(len(issues), 1)
        result = self.run_validator("read-only-leak")
        output = result.stdout + result.stderr
        self.assertEqual(result.returncode, 1, output)
        self.assertIn("[read-only] leaky", output)

    def test_tight_fixture_has_no_read_only_issue(self):
        result = self.run_validator("read-only-ok")
        self.assertNotIn("[read-only]", result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
