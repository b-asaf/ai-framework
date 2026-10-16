import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tools"))

import validate_framework  # noqa: E402
from validate_framework import Agent  # noqa: E402


def make_agent(permission):
    return Agent(path=Path("agents") / "x.md", mode=None, model=None, permission=permission, task_permissions={})


def allows():
    return {rule: "allow" for rule in validate_framework.GIT_CONTEXT_ALLOWS}


class GitContextAllowTest(unittest.TestCase):
    def test_ask_agent_with_allows_after_fallback_is_clean(self):
        bash = {"*": "ask"}
        bash.update(allows())
        self.assertEqual(validate_framework.lint_git_context(make_agent({"bash": bash})), [])

    def test_ask_agent_without_allows_is_reported(self):
        issues = validate_framework.lint_git_context(make_agent({"bash": {"*": "ask"}}))
        self.assertEqual(len(issues), 2)
        self.assertEqual(issues[0].check, "git-context")

    def test_allow_before_fallback_is_reported(self):
        bash = allows()
        bash["*"] = "ask"
        issues = validate_framework.lint_git_context(make_agent({"bash": bash}))
        self.assertEqual(len(issues), 2)
        self.assertIn("comes before", issues[0].message)

    def test_deny_agent_is_exempt(self):
        self.assertEqual(validate_framework.lint_git_context(make_agent({"bash": {"*": "deny"}})), [])

    def test_agent_without_bash_block_is_exempt(self):
        self.assertEqual(validate_framework.lint_git_context(make_agent({})), [])


if __name__ == "__main__":
    unittest.main()
