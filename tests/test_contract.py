import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from execution.runner import contract  # noqa: E402


def messages(instance, schema):
    return " | ".join(contract.validate(instance, schema))


class Checker(unittest.TestCase):
    def test_type_mismatch_names_the_path_and_the_kind(self):
        text = messages({"a": "x"}, {"type": "object", "properties": {"a": {"type": "integer"}}})
        self.assertIn("$.a", text)
        self.assertIn("string", text)

    def test_a_boolean_is_not_an_integer(self):
        self.assertIn("boolean", messages(True, {"type": "integer"}))

    def test_a_type_list_allows_null(self):
        schema = {"type": ["string", "null"]}
        self.assertEqual(contract.validate(None, schema), [])
        self.assertNotEqual(contract.validate(3, schema), [])

    def test_missing_required_property(self):
        self.assertIn("missing 'a'", messages({}, {"type": "object", "required": ["a"]}))

    def test_unexpected_property_only_when_additional_is_false(self):
        schema = {"type": "object", "properties": {"a": {}}}
        self.assertEqual(contract.validate({"b": 1}, schema), [])
        strict = dict(schema, additionalProperties=False)
        self.assertIn("unexpected 'b'", messages({"b": 1}, strict))

    def test_enum(self):
        self.assertEqual(contract.validate("a", {"enum": ["a", "b"]}), [])
        self.assertIn("not one of", messages("c", {"enum": ["a", "b"]}))

    def test_items_report_the_index(self):
        schema = {"type": "object", "properties": {"a": {"type": "array", "items": {"type": "integer"}}}}
        self.assertIn("$.a[1]", messages({"a": [1, "x"]}, schema))

    def test_min_length_and_minimum(self):
        self.assertNotEqual(contract.validate("", {"type": "string", "minLength": 1}), [])
        self.assertIn("below 1", messages(0, {"type": "integer", "minimum": 1}))
        self.assertEqual(contract.validate(None, {"type": ["integer", "null"], "minimum": 1}), [])

    def test_check_schema_rejects_what_it_cannot_enforce(self):
        with self.assertRaisesRegex(contract.ContractError, "pattern"):
            contract.check_schema({"type": "string", "pattern": "x"})
        with self.assertRaisesRegex(contract.ContractError, "oneOf"):
            contract.check_schema({"properties": {"a": {"oneOf": []}}})

    def test_check_schema_rejects_unknown_types_and_schema_valued_additional_properties(self):
        with self.assertRaises(contract.ContractError):
            contract.check_schema({"type": "text"})
        with self.assertRaises(contract.ContractError):
            contract.check_schema({"additionalProperties": {"type": "string"}})

    def test_load_schema_missing_and_unreadable(self):
        with self.assertRaises(contract.ContractError):
            contract.load_schema("no-such-contract")
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "broken.schema.json").write_text("{bad", encoding="utf-8")
            with mock.patch.object(contract, "SCHEMA_DIR", Path(tmp)):
                with self.assertRaisesRegex(contract.ContractError, "broken.schema.json"):
                    contract.load_schema("broken")


FINDING = {"severity": "BLOCKING", "category": "ERROR HANDLING", "message": "Swallowed exception.", "file": "src/a.ts", "line": 12}


def report(**changes):
    return dict({"verdict": "APPROVED", "summary": "Fine.", "findings": []}, **changes)


class ReviewReportSchema(unittest.TestCase):
    def problems(self, instance):
        return contract.validate_contract(instance, "review-report")

    def test_minimal_and_full_reports_are_valid(self):
        self.assertEqual(self.problems(report()), [])
        cross_file = {"severity": "NON-BLOCKING", "category": "NAMING", "message": "Unclear name."}
        self.assertEqual(self.problems(report(verdict="REQUEST CHANGES", findings=[FINDING, cross_file])), [])

    def test_unknown_verdict_is_flagged(self):
        self.assertIn("verdict", " ".join(self.problems(report(verdict="LGTM"))))

    def test_empty_summary_is_flagged(self):
        self.assertIn("summary", " ".join(self.problems(report(summary=""))))

    def test_findings_must_be_a_list(self):
        self.assertNotEqual(self.problems(report(findings="none")), [])

    def test_finding_without_a_message_is_flagged(self):
        broken = {key: value for key, value in FINDING.items() if key != "message"}
        self.assertIn("missing 'message'", " ".join(self.problems(report(findings=[broken]))))

    def test_finding_with_a_bad_severity_or_line(self):
        self.assertNotEqual(self.problems(report(findings=[dict(FINDING, severity="MAJOR")])), [])
        self.assertNotEqual(self.problems(report(findings=[dict(FINDING, line=0)])), [])

    def test_extra_properties_are_flagged(self):
        self.assertIn("unexpected 'extra'", " ".join(self.problems(report(extra=1))))


FIELDS = [
    "run_id", "timestamp", "role", "profile", "runtime", "requested_model", "resolved_model",
    "policy_result", "fallback", "input_artifacts", "output_artifacts", "status", "stop_reason",
    "tokens", "cost", "duration_ms", "verification", "error",
]


def record(**changes):
    base = {
        "run_id": "r1",
        "timestamp": "2026-10-21T10:00:00Z",
        "role": "reviewer",
        "profile": "default",
        "runtime": "rt",
        "requested_model": "m/one",
        "resolved_model": "m/one",
        "policy_result": "pass",
        "fallback": False,
        "input_artifacts": ["diff.patch"],
        "output_artifacts": ["review.json"],
        "status": {"execution": "success", "artifact": "success", "workflow": "success"},
        "stop_reason": "stop",
        "tokens": {"input": 10, "output": 5},
        "cost": 0.01,
        "duration_ms": 1200,
        "verification": None,
        "error": None,
    }
    return dict(base, **changes)


class RunRecordSchema(unittest.TestCase):
    def problems(self, instance):
        return contract.validate_contract(instance, "run-record")

    def test_requires_exactly_the_fields_of_plan_5_4(self):
        schema = contract.load_schema("run-record")
        self.assertEqual(sorted(schema["required"]), sorted(FIELDS))
        self.assertEqual(sorted(schema["properties"]), sorted(FIELDS + ["requested_effort", "resolved_effort"]))

    def test_a_complete_record_is_valid(self):
        self.assertEqual(self.problems(record()), [])

    def test_every_field_is_required(self):
        for field in FIELDS:
            with self.subTest(field=field):
                partial = {key: value for key, value in record().items() if key != field}
                self.assertIn(f"missing '{field}'", " ".join(self.problems(partial)))

    def test_a_failed_run_with_an_error_object_is_valid(self):
        failed = record(
            resolved_model=None,
            status={"execution": "failure", "artifact": "not_run", "workflow": "not_run"},
            error={"message": "boom", "stderr_tail": "x", "event_tail": ["a", "b"]},
        )
        self.assertEqual(self.problems(failed), [])

    def test_error_needs_a_message(self):
        self.assertIn("missing 'message'", " ".join(self.problems(record(error={"stderr_tail": "x"}))))

    def test_status_levels_are_checked(self):
        bad_value = {"execution": "ok", "artifact": "success", "workflow": "success"}
        self.assertNotEqual(self.problems(record(status=bad_value)), [])
        self.assertNotEqual(self.problems(record(status={"execution": "success"})), [])

    def test_extra_fields_are_flagged(self):
        self.assertIn("unexpected 'extra'", " ".join(self.problems(record(extra=1))))


if __name__ == "__main__":
    unittest.main()
