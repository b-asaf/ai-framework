import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tools"))

import validate_framework  # noqa: E402
from validate_framework import Agent  # noqa: E402


def make_agent(name, bash):
    return Agent(path=Path("agents") / (name + ".md"), mode=None, model=None,
                 permission={"bash": bash}, task_permissions={})


class CommitterFallbackTest(unittest.TestCase):
    def test_committer_with_deny_fallback_is_clean(self):
        bash = {"*": "deny", "git commit *": "allow"}
        self.assertEqual(validate_framework.lint_committer_fallback(make_agent("orchestrator", bash)), [])

    def test_committer_with_ask_fallback_is_reported(self):
        bash = {"*": "ask", "git commit *": "allow"}
        issues = validate_framework.lint_committer_fallback(make_agent("orchestrator", bash))
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].check, "committer-fallback")
        self.assertIn("found ask", issues[0].message)

    def test_committer_without_fallback_is_reported(self):
        issues = validate_framework.lint_committer_fallback(make_agent("orchestrator", {"git commit *": "allow"}))
        self.assertEqual(len(issues), 1)
        self.assertIn("<missing>", issues[0].message)

    def test_non_committer_is_exempt(self):
        self.assertEqual(validate_framework.lint_committer_fallback(make_agent("qa", {"*": "ask"})), [])


if __name__ == "__main__":
    unittest.main()
