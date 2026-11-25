import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from execution.verification.gates.pre_push import find_violations  # noqa: E402

MEASUREMENT = {"sha": "abc", "files": 10, "lines": 1, "paths": ["a.py"]}


class FindViolations(unittest.TestCase):
    def test_clean_push_is_clean(self):
        self.assertEqual(find_violations(["feature/x"], {}, {}, {}, 3, 60), [])

    def test_the_name_of_the_pushed_branch_is_not_judged(self):
        self.assertEqual(find_violations(["main"], {}, {}, {}, 3, 60), [])

    def test_dependency_change_is_tagged(self):
        violations = find_violations(
            ["feature/x"],
            {"feature/x": ["package.json"]}, {"feature/x": ["fix: bug"]}, {},
            3, 60,
        )
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["check"], "dependency_change")

    def test_dependency_change_with_trailer_is_clean(self):
        violations = find_violations(
            ["feature/x"],
            {"feature/x": ["package.json"]}, {"feature/x": ["Dependency-Approved: me"]}, {},
            3, 60,
        )
        self.assertEqual(violations, [])

    def test_quick_lane_over_limit_is_tagged(self):
        violations = find_violations(["feature/x"], {}, {}, {"feature/x": [MEASUREMENT]}, 3, 60)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["check"], "quick_lane")

    def test_skip_verification_skips_both_checks(self):
        violations = find_violations(
            ["feature/x"],
            {"feature/x": ["package.json"]}, {"feature/x": ["fix: bug"]}, {"feature/x": [MEASUREMENT]},
            3, 60, skip_verification=True,
        )
        self.assertEqual(violations, [])

    def test_missing_per_ref_data_defaults_to_empty(self):
        self.assertEqual(find_violations(["feature/x"], {}, {}, {}, 3, 60), [])

    def test_multiple_branches_combine_results_from_both_checks(self):
        violations = find_violations(
            ["main", "feature/x"],
            {"feature/x": ["package.json"]}, {"feature/x": []},
            {"feature/x": [MEASUREMENT]},
            3, 60,
        )
        checks = sorted(v["check"] for v in violations)
        self.assertEqual(checks, ["dependency_change", "quick_lane"])


if __name__ == "__main__":
    unittest.main()
