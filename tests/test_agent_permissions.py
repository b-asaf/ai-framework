"""The bash rules of the agents that run tests or read the git state (F31, F54).

OpenCode checks the parts of a chained command separately, so a trailing wildcard allow is safe. The last
matching rule wins, so an allow only works after the rule it overrides.
"""

import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tools"))

import validate_framework  # noqa: E402

AGENTS = {agent.name: agent for agent in validate_framework.discover_agents(REPO / "agents")}
TEST_RUNNERS = ("python -m unittest", "python -m unittest *")
LIZARD = "python -m lizard *"
PYTHON_RUNNERS = TEST_RUNNERS + (LIZARD,)


def bash(name):
    return AGENTS[name].permission["bash"]


def comes_after(rules, later, earlier):
    order = list(rules)
    return order.index(later) > order.index(earlier)


class GitStatusWithOptions(unittest.TestCase):
    def test_git_status_with_arguments_is_allowed_after_the_git_deny(self):
        for name in ("backend", "qa", "code-reviewer"):
            with self.subTest(agent=name):
                rules = bash(name)
                self.assertEqual(rules["git status *"], "allow")
                self.assertEqual(rules["git *"], "deny")
                self.assertTrue(comes_after(rules, "git status *", "git *"))
                self.assertTrue(comes_after(rules, "git status *", "*"))


class PythonRunners(unittest.TestCase):
    def test_backend_and_qa_allow_the_python_runners_after_the_fallback(self):
        for name in ("backend", "qa"):
            with self.subTest(agent=name):
                rules = bash(name)
                self.assertEqual(rules["*"], "ask")
                for rule in PYTHON_RUNNERS:
                    self.assertEqual(rules.get(rule), "allow", rule)
                    self.assertTrue(comes_after(rules, rule, "*"), rule)

    def test_the_read_only_reviewer_still_asks_before_running_repo_code(self):
        rules = bash("code-reviewer")
        self.assertEqual(rules["*"], "ask")
        for rule in TEST_RUNNERS:
            self.assertNotEqual(rules.get(rule), "allow", rule)

    def test_the_reviewer_may_run_lizard_which_only_reads_source_files(self):
        rules = bash("code-reviewer")
        self.assertEqual(rules.get(LIZARD), "allow")
        self.assertTrue(comes_after(rules, LIZARD, "*"))

    def test_the_repo_validator_is_not_allowed_in_the_generic_agents(self):
        for name in ("backend", "qa", "code-reviewer"):
            with self.subTest(agent=name):
                self.assertFalse([rule for rule in bash(name) if "validate_framework" in rule])


if __name__ == "__main__":
    unittest.main()
