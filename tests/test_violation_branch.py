"""Violations of the dependency and quick-lane checks name the pushed branch.

The key is `pushed_branch`; run._describe prints it as "(branch <name>)".
"""
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from execution.verification import run  # noqa: E402
from execution.verification.gates.pre_push import find_violations  # noqa: E402

SHA = "a" * 40


class PushedBranchInViolations(unittest.TestCase):
    def test_dependency_violation_names_the_pushed_branch(self):
        violations = find_violations(
            ["feature/x"],
            {"feature/x": ["package.json"]}, {"feature/x": ["fix: bug"]}, {},
            3, 60,
        )
        self.assertEqual(violations[0]["pushed_branch"], "feature/x")
        text = run._describe(violations[0])
        self.assertIn("package.json", text)
        self.assertIn("(branch feature/x)", text)
        self.assertNotIn("protected branch", text)

    def test_quick_lane_violation_names_the_pushed_branch(self):
        measurement = {"sha": SHA, "files": 10, "lines": 1, "paths": ["a.py"]}
        violations = find_violations(
            ["feature/x"], {}, {}, {"feature/x": [measurement]}, 3, 60,
        )
        self.assertEqual(violations[0]["pushed_branch"], "feature/x")
        text = run._describe(violations[0])
        self.assertIn("exceeds the quick-lane limits", text)
        self.assertIn("(branch feature/x)", text)

    def test_each_pushed_branch_is_named_separately(self):
        violations = find_violations(
            ["feature/a", "feature/b"],
            {"feature/a": ["package.json"], "feature/b": ["pom.xml"]},
            {"feature/a": ["fix: a"], "feature/b": ["fix: b"]}, {},
            3, 60,
        )
        named = {v["pushed_branch"]: run._describe(v) for v in violations}
        self.assertEqual(sorted(named), ["feature/a", "feature/b"])
        self.assertIn("package.json", named["feature/a"])
        self.assertIn("pom.xml", named["feature/b"])


if __name__ == "__main__":
    unittest.main()
