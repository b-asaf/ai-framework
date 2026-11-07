"""Report contracts per role (plan step 3B.1): the reviewer's contract and task message stay as they were,
and the qa role has its own contract."""

import hashlib
import json
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from execution.runner import contract, report  # noqa: E402

REVIEWER_MESSAGE_SHA256 = "c6c98c34b5e5b3074cd3e2cf11fb95a0fbc24dc99f58771bedda10a80842b3ab"
REVIEW = {"verdict": "APPROVED", "summary": "Fine.", "findings": []}
ENTRY = {"file": "src/sum.test.mjs", "count": 3, "covers": "empty list, one item, many items"}


def make_qa(**changes):
    base = {
        "outcome": "TESTS_WRITTEN", "summary": "Tests added.", "frameworks": ["node:test"],
        "tests_written": [ENTRY], "gaps": [], "production_issues": [],
    }
    return dict(base, **changes)


def joined(problems):
    return " | ".join(problems)


class ReviewerUnchanged(unittest.TestCase):
    def test_the_task_message_is_byte_for_byte_what_it_was(self):
        digest = hashlib.sha256(report.task_message().encode("utf-8")).hexdigest()
        self.assertEqual(
            digest, REVIEWER_MESSAGE_SHA256,
            "The reviewer task message changed. Its wording decides whether models reply with JSON only "
            "(F45, F49 to F51): rerun the reviewer benchmark, then update the hash on purpose.",
        )

    def test_the_reviewer_is_the_default_role(self):
        self.assertEqual(report.task_message(), report.task_message("code-reviewer"))
        self.assertEqual(report.check_report(REVIEW), report.check_report(REVIEW, "code-reviewer"))
        self.assertEqual(report.parse_report(json.dumps(REVIEW)).status, "success")

    def test_a_qa_report_is_not_a_review(self):
        self.assertEqual(report.parse_report(json.dumps(make_qa())).status, "failure")


class QaReport(unittest.TestCase):
    def test_a_report_with_tests_is_valid(self):
        self.assertEqual(report.check_report(make_qa(), "qa"), [])

    def test_no_tests_needed_is_valid_without_tests(self):
        data = make_qa(outcome="NO_TESTS_NEEDED", tests_written=[])
        self.assertEqual(report.check_report(data, "qa"), [])

    def test_needs_developer_is_valid_with_a_gap(self):
        data = make_qa(outcome="NEEDS_DEVELOPER", tests_written=[], gaps=["No test file pattern is recorded."])
        self.assertEqual(report.check_report(data, "qa"), [])

    def test_written_tests_need_an_entry(self):
        problems = report.check_report(make_qa(tests_written=[]), "qa")
        self.assertIn("at least one entry in tests_written", joined(problems))

    def test_other_outcomes_cannot_list_tests(self):
        problems = report.check_report(make_qa(outcome="NO_TESTS_NEEDED"), "qa")
        self.assertIn("cannot list tests_written", joined(problems))

    def test_needs_developer_without_a_gap_is_flagged(self):
        problems = report.check_report(make_qa(outcome="NEEDS_DEVELOPER", tests_written=[]), "qa")
        self.assertIn("needs at least one gap", joined(problems))

    def test_a_file_listed_twice_is_flagged(self):
        problems = report.check_report(make_qa(tests_written=[ENTRY, ENTRY]), "qa")
        self.assertIn("lists a file twice: src/sum.test.mjs", joined(problems))

    def test_schema_problems_are_reported(self):
        cases = (
            ({key: value for key, value in make_qa().items() if key != "gaps"}, "missing 'gaps'"),
            (make_qa(verdict="APPROVED"), "unexpected 'verdict'"),
            (make_qa(outcome="DONE"), "is not one of"),
            (make_qa(tests_written=[dict(ENTRY, count=0)]), "is below 1"),
        )
        for data, expected in cases:
            with self.subTest(expected=expected):
                self.assertIn(expected, joined(report.check_report(data, "qa")))


class QaReply(unittest.TestCase):
    def test_a_fenced_json_reply_is_read(self):
        check = report.parse_report("```json\n" + json.dumps(make_qa()) + "\n```", "qa")
        self.assertEqual(check.status, "success")
        self.assertEqual(check.report["outcome"], "TESTS_WRITTEN")

    def test_prose_around_the_json_is_refused(self):
        check = report.parse_report("Here is my report: " + json.dumps(make_qa()), "qa")
        self.assertEqual(check.status, "failure")
        self.assertIn("not one JSON object", joined(check.problems))

    def test_a_review_is_not_a_qa_report(self):
        self.assertEqual(report.parse_report(json.dumps(REVIEW), "qa").status, "failure")


class QaTaskMessage(unittest.TestCase):
    def test_the_message_carries_the_schema_and_the_rules(self):
        text = report.task_message("qa")
        self.assertIn('"outcome"', text)
        for rule in report.QA_RULES:
            with self.subTest(rule=rule):
                self.assertIn(rule, text)

    def test_the_message_is_not_the_reviewers(self):
        text = report.task_message("qa")
        self.assertNotIn("BLOCKING", text)
        self.assertNotEqual(text, report.task_message())

    def test_the_schema_is_one_the_checker_can_enforce(self):
        self.assertEqual(contract.load_schema("qa-report")["title"], "QAReport")


class UnknownRole(unittest.TestCase):
    def test_every_entry_point_refuses_an_unknown_role(self):
        calls = (
            lambda: report.task_message("nobody"),
            lambda: report.check_report({}, "nobody"),
            lambda: report.parse_report("{}", "nobody"),
        )
        for call in calls:
            with self.subTest(call=call):
                with self.assertRaisesRegex(contract.ContractError, "no report contract"):
                    call()


if __name__ == "__main__":
    unittest.main()
