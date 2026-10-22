"""Tests for the OpenCode adapter.

tests/fixtures/opencode-run/ holds output of real runs on OpenCode 1.19.3
(captured 2026-10-22): review.jsonl is the event stream of a primary agent, the
two session exports are trimmed to the fields the adapter reads, and
fallback.stderr is the warning of a subagent started with --agent (F6).
Synthetic events are used only where no real sample exists, for example the
error event.
"""

import json
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from execution.runner import opencode_adapter as adapter  # noqa: E402
from execution.runner import record, report  # noqa: E402

FIXTURES = REPO / "tests" / "fixtures" / "opencode-run"
AGENT = "sample-reviewer"
MODEL = "github-copilot/claude-haiku-4.5"
OTHER_MODEL = "github-copilot/claude-sonnet-5"


def read(name):
    return (FIXTURES / name).read_text(encoding="utf-8")


def event(kind, **part):
    return json.dumps({"type": kind, "sessionID": "ses_x", "part": part})


def stream(*events):
    return "\n".join(events) + "\n"


def export(*infos):
    return json.dumps({"info": {}, "messages": [{"info": info} for info in infos]})


class ParseEvents(unittest.TestCase):
    def test_the_real_run_is_read(self):
        events = adapter.parse_events(read("review.jsonl"))
        self.assertEqual(events.session_id, "ses_e9d71c4f5ffeVnSOlPgSptN79x")
        self.assertEqual(events.reason, "stop")
        self.assertEqual(events.errors, ())
        self.assertEqual(events.bad_lines, 0)
        self.assertEqual(report.parse_report(events.reply).status, "success")

    def test_tokens_and_cost_of_the_real_run(self):
        events = adapter.parse_events(read("review.jsonl"))
        self.assertEqual(
            events.tokens,
            {"total": 9161, "input": 3, "output": 183, "reasoning": 0, "cache": {"write": 8975, "read": 0}},
        )
        self.assertEqual(events.cost, 0.01213675)

    def test_several_steps_are_summed_and_the_last_text_and_reason_win(self):
        text = stream(
            event("step_start"),
            event("step_finish", reason="tool-calls", tokens={"total": 10, "input": 4, "cache": {"write": 1, "read": 2}}, cost=0.5),
            event("text", text="first"),
            event("step_finish", reason="stop", tokens={"total": 20, "input": 6, "cache": {"write": 3, "read": 0}}, cost=0.25),
            event("text", text="last"),
        )
        events = adapter.parse_events(text)
        self.assertEqual(events.reply, "last")
        self.assertEqual(events.reason, "stop")
        self.assertEqual(events.tokens, {"total": 30, "input": 10, "cache": {"write": 4, "read": 2}})
        self.assertEqual(events.cost, 0.75)

    def test_an_empty_stream_has_nothing(self):
        self.assertEqual(adapter.parse_events(""), adapter.RunEvents(None, None, None, None, None, (), 0))

    def test_an_error_event_is_kept(self):
        # Synthetic: no real error sample has been captured yet.
        events = adapter.parse_events(stream(json.dumps({"type": "error", "error": {"message": "boom"}})))
        self.assertEqual(len(events.errors), 1)
        self.assertIn("boom", events.errors[0])

    def test_lines_that_are_not_json_objects_are_counted_and_blank_lines_ignored(self):
        text = '{"a":\nnot json\n\n[1]\n' + event("text", text="hi") + "\n"
        events = adapter.parse_events(text)
        self.assertEqual(events.bad_lines, 3)
        self.assertEqual(events.reply, "hi")

    def test_a_text_event_without_text_does_not_replace_the_reply(self):
        events = adapter.parse_events(stream(event("text", text="first"), event("text", id="x")))
        self.assertEqual(events.reply, "first")

    def test_a_step_finish_without_usage_leaves_tokens_and_cost_empty(self):
        events = adapter.parse_events(stream(event("text", text="hi"), event("step_finish", reason="stop")))
        self.assertEqual((events.reason, events.tokens, events.cost), ("stop", None, None))


class FallbackWarnings(unittest.TestCase):
    def test_the_real_warning_is_found(self):
        warnings = adapter.fallback_warnings(read("fallback.stderr"))
        self.assertEqual(len(warnings), 1)
        self.assertIn("sample-sub", warnings[0])

    def test_clean_stderr_has_no_warning(self):
        self.assertEqual(adapter.fallback_warnings(""), [])
        self.assertEqual(adapter.fallback_warnings("some other warning\n"), [])

    def test_only_the_matching_lines_are_returned(self):
        text = "x\n!  agent a is a subagent. Falling back to default agent\ny\n"
        self.assertEqual(adapter.fallback_warnings(text), ["!  agent a is a subagent. Falling back to default agent"])


class ParseExport(unittest.TestCase):
    def test_the_real_review_session(self):
        self.assertEqual(adapter.parse_export(read("review-session.json")), adapter.RanInfo(AGENT, MODEL, "stop"))

    def test_the_real_fallback_session_ran_as_the_default_agent(self):
        self.assertEqual(adapter.parse_export(read("fallback-session.json")), adapter.RanInfo("build", MODEL, "stop"))

    def test_the_last_assistant_message_wins(self):
        text = export(
            {"role": "user"},
            {"role": "assistant", "agent": "a", "providerID": "p", "modelID": "m1", "finish": "tool-calls"},
            {"role": "assistant", "agent": "b", "providerID": "p", "modelID": "m2", "finish": "stop"},
        )
        self.assertEqual(adapter.parse_export(text), adapter.RanInfo("b", "p/m2", "stop"))

    def test_no_assistant_message_raises(self):
        with self.assertRaisesRegex(adapter.AdapterError, "no assistant message"):
            adapter.parse_export(export({"role": "user"}))

    def test_text_that_is_not_json_raises(self):
        with self.assertRaisesRegex(adapter.AdapterError, "not JSON"):
            adapter.parse_export("{bad")

    def test_an_export_without_messages_raises(self):
        with self.assertRaisesRegex(adapter.AdapterError, "no messages"):
            adapter.parse_export('{"info": {}}')

    def test_a_message_without_a_model_gives_none(self):
        text = export({"role": "assistant", "agent": "a", "providerID": "p"})
        self.assertEqual(adapter.parse_export(text), adapter.RanInfo("a", None, None))


class CheckModelRan(unittest.TestCase):
    def test_what_was_requested_is_clean(self):
        self.assertEqual(adapter.check_model_ran(adapter.RanInfo(AGENT, MODEL, "stop"), AGENT, MODEL), [])

    def test_a_different_agent_is_flagged(self):
        problems = adapter.check_model_ran(adapter.RanInfo("build", MODEL, "stop"), AGENT, MODEL)
        self.assertEqual(len(problems), 1)
        self.assertIn("F6", problems[0])
        self.assertIn("'build'", problems[0])

    def test_a_different_model_is_flagged(self):
        problems = adapter.check_model_ran(adapter.RanInfo(AGENT, OTHER_MODEL, "stop"), AGENT, MODEL)
        self.assertEqual(len(problems), 1)
        self.assertIn("F34", problems[0])

    def test_both_differences_are_reported(self):
        self.assertEqual(len(adapter.check_model_ran(adapter.RanInfo("build", OTHER_MODEL, "stop"), AGENT, MODEL)), 2)


def assess(stderr="", session="review-session.json", events=None, model=MODEL):
    text = read("review.jsonl") if events is None else events
    return adapter.assess(adapter.parse_events(text), stderr, adapter.parse_export(read(session)), AGENT, model)


def record_fields(result, **changes):
    fields = {
        "role": "code-reviewer",
        "profile": "default",
        "runtime": "opencode",
        "requested_model": MODEL,
        "resolved_model": result.resolved_model,
        "policy_result": "pass",
        "fallback": result.fallback,
        "input_artifacts": ["sample.patch"],
        "output_artifacts": [],
        "status": record.status_levels(result.status),
        "stop_reason": result.stop_reason,
        "tokens": result.tokens,
        "cost": result.cost,
        "duration_ms": 1000,
        "verification": None,
        "error": None,
    }
    return dict(fields, **changes)


class Assess(unittest.TestCase):
    def test_the_real_run_is_a_success(self):
        result = assess()
        self.assertEqual(result.status, "success")
        self.assertEqual(result.problems, ())
        self.assertFalse(result.fallback)
        self.assertEqual((result.resolved_model, result.stop_reason, result.cost), (MODEL, "stop", 0.01213675))
        self.assertEqual(result.tokens["total"], 9161)
        self.assertEqual(report.parse_report(result.reply).status, "success")

    def test_a_success_fits_the_run_record(self):
        result = assess()
        built = record.build_record(**record_fields(result))
        self.assertEqual(built["resolved_model"], MODEL)

    def test_the_fallback_is_a_failure_from_stderr_and_from_the_export(self):
        result = assess(read("fallback.stderr"), session="fallback-session.json")
        self.assertEqual(result.status, "failure")
        self.assertTrue(result.fallback)
        text = " | ".join(result.problems)
        self.assertIn("stderr", text)
        self.assertIn("'build'", text)

    def test_a_wrong_model_is_a_failure_that_still_fits_the_run_record(self):
        result = assess(model=OTHER_MODEL)
        self.assertEqual(result.status, "failure")
        self.assertFalse(result.fallback)
        self.assertIn("F34", " ".join(result.problems))
        self.assertEqual(result.resolved_model, MODEL)
        fields = record_fields(result, requested_model=OTHER_MODEL, error=record.error_info("; ".join(result.problems)))
        self.assertEqual(record.build_record(**fields)["status"]["execution"], "failure")

    def test_an_error_event_is_a_failure(self):
        events = read("review.jsonl") + json.dumps({"type": "error", "error": {"message": "boom"}}) + "\n"
        result = assess(events=events)
        self.assertEqual(result.status, "failure")
        self.assertIn("error event", " ".join(result.problems))

    def test_a_run_that_did_not_stop_normally_is_a_failure(self):
        result = assess(events=stream(event("text", text="x"), event("step_finish", reason="length")))
        self.assertEqual(result.status, "failure")
        self.assertIn("did not stop normally", " ".join(result.problems))

    def test_a_run_without_a_reply_is_a_failure(self):
        result = assess(events=stream(event("step_finish", reason="stop")))
        self.assertEqual(result.status, "failure")
        self.assertIn("no text event", " ".join(result.problems))

    def test_lines_that_are_not_events_are_a_failure(self):
        result = assess(events=read("review.jsonl") + "warning: something\n")
        self.assertEqual(result.status, "failure")
        self.assertIn("not JSON", " ".join(result.problems))


if __name__ == "__main__":
    unittest.main()
