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


def allows():
    return {rule: "allow" for rule in validate_framework.TEST_RUNNER_ALLOWS}


class TestRunnerAllowTest(unittest.TestCase):
    def test_qa_with_allows_after_fallback_is_clean(self):
        bash = {"*": "ask"}
        bash.update(allows())
        self.assertEqual(validate_framework.lint_test_runners(make_agent("qa", bash)), [])

    def test_qa_without_allows_is_reported(self):
        issues = validate_framework.lint_test_runners(make_agent("qa", {"*": "ask"}))
        self.assertEqual(len(issues), len(validate_framework.TEST_RUNNER_ALLOWS))
        self.assertEqual(issues[0].check, "test-runner")

    def test_allow_before_fallback_is_reported(self):
        bash = allows()
        bash["*"] = "ask"
        issues = validate_framework.lint_test_runners(make_agent("qa", bash))
        self.assertEqual(len(issues), len(validate_framework.TEST_RUNNER_ALLOWS))
        self.assertIn("comes before", issues[0].message)

    def test_other_agents_are_exempt(self):
        self.assertEqual(validate_framework.lint_test_runners(make_agent("gatekeeper", {"*": "ask"})), [])


if __name__ == "__main__":
    unittest.main()
