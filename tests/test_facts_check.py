import json
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from execution.runner import facts, facts_check  # noqa: E402
from execution.runner.tree import Changes  # noqa: E402

PASSED = facts.TestOutcome(0, False, ("ok",), 1)
FAILED = facts.TestOutcome(1, False, ("not ok",), 1)


def written(*names):
    return [{"file": name, "count": 1, "covers": "x"} for name in names]


class CrossCheck(unittest.TestCase):
    def test_a_report_that_matches_the_tree_has_no_problems(self):
        changes = Changes(added=("src/a.test.ts",), modified=("src/b.test.ts",))
        self.assertEqual(facts_check.cross_check(written("src/a.test.ts", "src/b.test.ts"), changes), [])

    def test_a_listed_file_that_did_not_change_is_a_problem(self):
        problems = facts_check.cross_check(written("src/a.test.ts"), Changes())
        self.assertEqual(len(problems), 1)
        self.assertIn("src/a.test.ts", problems[0])

    def test_every_unreported_change_is_a_problem(self):
        changes = Changes(added=("a.test.ts",), modified=("src/a.ts",), deleted=("old.ts",))
        problems = facts_check.cross_check(written(), changes)
        self.assertEqual(len(problems), 3)
        self.assertTrue(all("not in tests_written" in problem for problem in problems))

    def test_a_listed_file_that_was_deleted_is_one_problem(self):
        self.assertEqual(len(facts_check.cross_check(written("a.test.ts"), Changes(deleted=("a.test.ts",)))), 1)

    def test_path_spelling_does_not_matter(self):
        changes = Changes(added=("src/a.test.ts",))
        self.assertEqual(facts_check.cross_check(written(".\\src\\a.test.ts"), changes), [])


class Workflow(unittest.TestCase):
    def test_success_needs_passing_tests_and_no_problems(self):
        self.assertEqual(facts_check.workflow_level(PASSED, []), "success")
        self.assertEqual(facts_check.workflow_level(FAILED, []), "failure")
        self.assertEqual(facts_check.workflow_level(PASSED, ["x"]), "failure")

    def test_the_verification_object_is_plain_json(self):
        built = facts_check.build_verification("node --test", FAILED, Changes(added=("a.test.ts",)), ["x"])
        self.assertEqual(json.loads(json.dumps(built)), built)
        self.assertEqual(built["tests"]["exit_code"], 1)
        self.assertEqual(built["changed_files"]["added"], ["a.test.ts"])
        self.assertEqual(built["problems"], ["x"])


class Outcome(unittest.TestCase):
    def test_needs_developer_lists_the_gaps(self):
        problems = facts_check.outcome_problems({"outcome": "NEEDS_DEVELOPER", "gaps": ["a", "b"]})
        self.assertEqual(problems, ["qa needs a decision from the developer: a; b"])

    def test_the_other_outcomes_have_no_problem(self):
        for outcome in ("TESTS_WRITTEN", "NO_TESTS_NEEDED"):
            self.assertEqual(facts_check.outcome_problems({"outcome": outcome, "gaps": []}), [])


if __name__ == "__main__":
    unittest.main()
