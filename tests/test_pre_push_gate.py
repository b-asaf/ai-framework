import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from execution.verification.gates.pre_push import find_violations  # noqa: E402

PROTECTED = ["main"]


class FindViolations(unittest.TestCase):
    def test_clean_push_is_clean(self):
        violations = find_violations(["feature/x"], PROTECTED, {}, {}, {}, 3, 60)
        self.assertEqual(violations, [])

    def test_protected_branch_push_is_tagged(self):
        violations = find_violations(["main"], PROTECTED, {}, {}, {}, 3, 60)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["check"], "branch_protection")

    def test_dependency_change_is_tagged(self):
        violations = find_violations(
            ["feature/x"], PROTECTED,
            {"feature/x": ["package.json"]}, {"feature/x": ["fix: bug"]}, {},
            3, 60,
        )
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["check"], "dependency_change")

    def test_dependency_change_with_trailer_is_clean(self):
        violations = find_violations(
            ["feature/x"], PROTECTED,
            {"feature/x": ["package.json"]}, {"feature/x": ["Dependency-Approved: me"]}, {},
            3, 60,
        )
        self.assertEqual(violations, [])

    def test_quick_lane_over_limit_is_tagged(self):
        measurement = {"sha": "abc", "files": 10, "lines": 1, "paths": ["a.py"]}
        violations = find_violations(
            ["feature/x"], PROTECTED, {}, {}, {"feature/x": [measurement]}, 3, 60,
        )
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["check"], "quick_lane")

    def test_skip_verification_skips_dependency_change_and_quick_lane(self):
        measurement = {"sha": "abc", "files": 10, "lines": 1, "paths": ["a.py"]}
        violations = find_violations(
            ["feature/x"], PROTECTED,
            {"feature/x": ["package.json"]}, {"feature/x": ["fix: bug"]}, {"feature/x": [measurement]},
            3, 60, skip_verification=True,
        )
        self.assertEqual(violations, [])

    def test_skip_verification_never_skips_branch_protection(self):
        violations = find_violations(["main"], PROTECTED, {}, {}, {}, 3, 60, skip_verification=True)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["check"], "branch_protection")

    def test_missing_per_ref_data_defaults_to_empty(self):
        violations = find_violations(["feature/x"], PROTECTED, {}, {}, {}, 3, 60)
        self.assertEqual(violations, [])

    def test_multiple_branches_combine_results_from_all_checks(self):
        measurement = {"sha": "abc", "files": 10, "lines": 1, "paths": ["a.py"]}
        violations = find_violations(
            ["main", "feature/x"], PROTECTED,
            {"feature/x": ["package.json"]}, {"feature/x": []},
            {"feature/x": [measurement]},
            3, 60,
        )
        checks = sorted(v["check"] for v in violations)
        self.assertEqual(checks, ["branch_protection", "dependency_change", "quick_lane"])


if __name__ == "__main__":
    unittest.main()
