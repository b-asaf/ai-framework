import json
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from execution.runner import contract, report  # noqa: E402

BLOCKING = {
    "severity": "BLOCKING",
    "category": "ERROR HANDLING",
    "message": "Swallowed exception.",
    "file": "src/a.ts",
    "line": 12,
}
NOTE = {"severity": "NON-BLOCKING", "category": "NAMING", "message": "Unclear name."}


def make(**changes):
    return dict({"verdict": "APPROVED", "summary": "Fine.", "findings": []}, **changes)


def joined(problems):
    return " | ".join(problems)


class CheckReport(unittest.TestCase):
    def test_a_clean_approval_is_valid(self):
        self.assertEqual(report.check_report(make()), [])

    def test_request_changes_with_a_blocking_finding_is_valid(self):
        self.assertEqual(report.check_report(make(verdict="REQUEST CHANGES", findings=[BLOCKING, NOTE])), [])

    def test_request_changes_without_a_blocking_finding_is_flagged(self):
        problems = report.check_report(make(verdict="REQUEST CHANGES", findings=[NOTE]))
        self.assertIn("needs at least one BLOCKING finding", joined(problems))

    def test_approval_with_a_blocking_finding_is_flagged(self):
        problems = report.check_report(make(verdict="APPROVED", findings=[BLOCKING]))
        self.assertIn("cannot have a BLOCKING finding", joined(problems))

    def test_advisory_notes_with_only_non_blocking_findings_is_valid(self):
        self.assertEqual(report.check_report(make(verdict="APPROVED WITH ADVISORY NOTES", findings=[NOTE])), [])

    def test_advisory_notes_with_a_blocking_finding_is_flagged(self):
        problems = report.check_report(make(verdict="APPROVED WITH ADVISORY NOTES", findings=[BLOCKING]))
        self.assertIn("cannot have a BLOCKING finding", joined(problems))

    def test_a_line_without_a_file_is_flagged(self):
        problems = report.check_report(make(findings=[dict(NOTE, line=3)]))
        self.assertIn("$.findings[0]", joined(problems))
        self.assertIn("needs a file", joined(problems))

    def test_schema_problems_come_first_and_stop_the_rules(self):
        problems = report.check_report(make(verdict="LGTM", findings=[BLOCKING]))
        self.assertIn("not one of", joined(problems))
        self.assertNotIn("BLOCKING finding", joined(problems))

    def test_something_that_is_not_an_object_is_flagged(self):
        self.assertIn("expected object", joined(report.check_report([])))


class ParseReport(unittest.TestCase):
    def test_plain_json_is_a_success(self):
        check = report.parse_report(json.dumps(make()))
        self.assertEqual(check.report, make())
        self.assertEqual(check.problems, ())
        self.assertEqual(check.status, "success")

    def test_json_in_a_fence_with_a_language_is_a_success(self):
        check = report.parse_report("```json\n" + json.dumps(make()) + "\n```")
        self.assertEqual(check.report, make())

    def test_json_in_a_plain_fence_with_whitespace_around_is_a_success(self):
        check = report.parse_report("\n  ```\n" + json.dumps(make(), indent=2) + "\n```\n")
        self.assertEqual(check.status, "success")

    def test_a_reply_that_gives_up_is_a_failure(self):
        check = report.parse_report("I couldn't complete the review.")
        self.assertIsNone(check.report)
        self.assertEqual(check.status, "failure")
        self.assertIn("not one JSON object", check.problems[0])

    def test_an_analysis_before_a_fenced_report_is_still_a_failure(self):
        # The shape of the first live reply (2026-10-23): analysis text, then one fenced block.
        fence = "`" * 3
        reply = "## Analysis\n\nThe loop runs one step too far.\n\n" + fence + "json\n" + json.dumps(make()) + "\n" + fence
        check = report.parse_report(reply)
        self.assertEqual(check.status, "failure")
        self.assertIn("not one JSON object", check.problems[0])

    def test_json_inside_prose_is_a_failure(self):
        check = report.parse_report("Here you go: " + json.dumps(make()))
        self.assertEqual(check.status, "failure")

    def test_a_report_that_breaks_the_schema_is_a_failure(self):
        check = report.parse_report(json.dumps(make(verdict="LGTM")))
        self.assertIsNone(check.report)
        self.assertIn("verdict", joined(check.problems))

    def test_a_reply_that_is_not_text_is_a_failure(self):
        check = report.parse_report(None)
        self.assertEqual(check.status, "failure")
        self.assertIn("not text", check.problems[0])


class TaskMessage(unittest.TestCase):
    def test_it_contains_the_schema_file_itself(self):
        schema = json.dumps(contract.load_schema("review-report"), indent=2)
        self.assertIn(schema, report.task_message())

    def test_it_states_the_rules_the_schema_cannot_express(self):
        message = report.task_message()
        for rule in report.RULES:
            self.assertIn(rule, message)

    def test_it_says_the_json_overrides_the_output_format_in_the_agent_instructions(self):
        message = report.task_message()
        self.assertIn("overrides any output format", message)
        self.assertIn("no text before it", message)


if __name__ == "__main__":
    unittest.main()
