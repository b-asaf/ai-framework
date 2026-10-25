"""Tests for the runner. A fake subprocess replays the real OpenCode output in
tests/fixtures/opencode-run/ (captured 2026-10-22 on OpenCode 1.19.3)."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tools"))

from execution.runner import opencode_adapter as adapter  # noqa: E402
from execution.runner import preflight, record, report, resolve, run  # noqa: E402
from lib.opencode_resolved import ResolvedModelError  # noqa: E402

FIXTURES = REPO / "tests" / "fixtures" / "opencode-run"
ROLE = "sample-reviewer"
MODEL = "github-copilot/claude-haiku-4.5"
SESSION = "ses_e9d71c4f5ffeVnSOlPgSptN79x"
AGENT = "---\ndescription: Fixture reviewer\nmode: subagent\npermission:\n  edit: deny\n---\nReview the diff.\n"
PATCH = "diff --git a/x b/x\n"
APPROVED = {"family": "Claude", "status": "approved", "evaluation": None}


def read(name):
    return (FIXTURES / name).read_text(encoding="utf-8")


def result(returncode=0, stdout="", stderr=""):
    return SimpleNamespace(returncode=returncode, stdout=stdout, stderr=stderr)


def event(kind, **part):
    return json.dumps({"type": kind, "sessionID": "ses_x", "part": part})


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def make_repo(base):
    root = base / "repo"
    policy = {"version": 1, "models": {MODEL: APPROVED}, "constraints": {"independence": []}}
    write_json(root / "execution" / "policy.json", policy)
    write_json(root / "execution" / "profiles" / "default.json", {"version": 1, "agents": {ROLE: {"model": MODEL}}})
    (root / "agents").mkdir(parents=True)
    (root / "agents" / f"{ROLE}.md").write_bytes(AGENT.encode("utf-8"))
    return root


class Fake:
    """Stands in for subprocess.run: replays recorded output and looks at the run folder while it exists."""

    def __init__(self, run_result=None, export_result=None):
        self.run_result = run_result if run_result is not None else result(0, read("review.jsonl"))
        self.export_result = export_result if export_result is not None else result(0, read("review-session.json"))
        self.calls = []
        self.seen = {}

    def __call__(self, command, **kwargs):
        self.calls.append((command, kwargs))
        if command[1] != "run":
            return self.export_result
        self.look_at_the_run_folder(command, kwargs["env"])
        if isinstance(self.run_result, Exception):
            raise self.run_result
        return self.run_result

    def look_at_the_run_folder(self, command, environment):
        config_dir = Path(environment["OPENCODE_CONFIG_DIR"])
        files = [command[i + 1] for i, argument in enumerate(command) if argument == "-f"]
        self.seen["config_dir"] = config_dir
        self.seen["agent"] = (config_dir / "agents" / f"{ROLE}.md").read_text(encoding="utf-8")
        self.seen["routing"] = json.loads(Path(environment["OPENCODE_CONFIG"]).read_text(encoding="utf-8"))
        self.seen["task"] = Path(files[0]).read_text(encoding="utf-8")


class RunReview(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base = Path(self.tmp.name)
        self.repo = make_repo(base)
        self.target = base / "target"
        self.target.mkdir()
        (self.target / "docs" / "project-overview").mkdir(parents=True)
        stack = self.target / "docs" / "project-overview" / "stack.md"
        stack.write_text("# Stack\n\n- Language: JavaScript\n", encoding="utf-8")
        (self.target / ".ai-framework.json").write_text("{}", encoding="utf-8")
        self.target_files = sorted(p.relative_to(self.target).as_posix() for p in self.target.rglob("*"))
        self.diff = base / "sample.patch"
        self.diff.write_text(PATCH, encoding="utf-8")

    def go(self, fake=None, role=ROLE, **kwargs):
        fake = fake if fake is not None else Fake()
        outcome = run.run_review(
            self.repo, self.target, role, self.diff, runner=fake, environ={"PATH": "p"}, which=lambda name: "oc", **kwargs
        )
        return outcome, fake

    def test_a_clean_run_is_an_execution_and_artifact_success(self):
        outcome, _ = self.go()
        built = outcome.record
        self.assertEqual(built["status"], {"execution": "success", "artifact": "success", "workflow": "not_run"})
        self.assertEqual((built["role"], built["profile"], built["runtime"]), (ROLE, "default", "opencode"))
        self.assertEqual((built["requested_model"], built["resolved_model"]), (MODEL, MODEL))
        self.assertEqual((built["policy_result"], built["fallback"], built["error"]), ("pass", False, None))
        self.assertEqual((built["stop_reason"], built["cost"]), ("stop", 0.01213675))
        self.assertEqual(built["input_artifacts"], ["sample.patch"])
        self.assertEqual(outcome.report["verdict"], "REQUEST CHANGES")

    def test_opencode_is_started_in_the_target_with_the_task_and_the_diff(self):
        _, fake = self.go()
        command, kwargs = fake.calls[0]
        self.assertEqual(command[:3], ["oc", "run", run.TASK_MESSAGE])
        self.assertEqual(command[command.index("--agent") + 1], ROLE)
        self.assertEqual(command[command.index("--format") + 1], "json")
        files = [command[i + 1] for i, argument in enumerate(command) if argument == "-f"]
        self.assertEqual(len(files), 2)
        self.assertEqual(files[1], self.diff.resolve().as_posix())
        self.assertEqual(Path(kwargs["cwd"]), self.target)
        self.assertEqual(fake.calls[1][0], ["oc", "export", SESSION])

    def test_the_run_folder_holds_a_primary_agent_and_the_routing_and_is_removed_afterwards(self):
        _, fake = self.go()
        self.assertIn("mode: primary", fake.seen["agent"])
        self.assertNotIn("model:", fake.seen["agent"])
        self.assertEqual(fake.seen["routing"]["agent"], {ROLE: {"model": MODEL}})
        self.assertEqual(fake.seen["task"], report.task_message())
        self.assertFalse(fake.seen["config_dir"].exists())
        self.assertFalse(fake.seen["config_dir"].parent.exists())

    def test_nothing_is_written_into_the_target(self):
        self.go()
        after = sorted(p.relative_to(self.target).as_posix() for p in self.target.rglob("*"))
        self.assertEqual(after, self.target_files)

    def test_a_fallback_warning_fails_the_run_without_an_export(self):
        outcome, fake = self.go(Fake(run_result=result(0, read("review.jsonl"), read("fallback.stderr"))))
        built = outcome.record
        self.assertEqual(len(fake.calls), 1)
        self.assertEqual(built["status"], {"execution": "failure", "artifact": "not_run", "workflow": "not_run"})
        self.assertTrue(built["fallback"])
        self.assertIsNone(built["resolved_model"])
        self.assertIn("Falling back", built["error"]["stderr_tail"])
        self.assertIsNone(outcome.report)

    def test_a_fallback_seen_only_in_the_export_fails_the_run(self):
        outcome, fake = self.go(Fake(export_result=result(0, read("fallback-session.json"))))
        built = outcome.record
        self.assertEqual(len(fake.calls), 2)
        self.assertEqual(built["status"]["execution"], "failure")
        self.assertTrue(built["fallback"])
        self.assertEqual(built["resolved_model"], MODEL)
        self.assertIn("F6", built["error"]["message"])

    def test_a_model_that_does_not_exist_fails_without_an_export(self):
        outcome, fake = self.go(Fake(run_result=result(1, read("bad-model.jsonl"))))
        built = outcome.record
        self.assertEqual(len(fake.calls), 1)
        self.assertEqual(built["status"]["execution"], "failure")
        self.assertIsNone(built["resolved_model"])
        self.assertIn("Model not found", built["error"]["message"])
        self.assertIn("exited with code 1", built["error"]["message"])

    def test_a_reply_that_is_not_a_report_is_execution_success_but_artifact_failure(self):
        lines = [event("step_start"), event("text", text="I could not complete the review"), event("step_finish", reason="stop")]
        outcome, _ = self.go(Fake(run_result=result(0, "\n".join(lines) + "\n")))
        built = outcome.record
        self.assertEqual(built["status"], {"execution": "success", "artifact": "failure", "workflow": "not_run"})
        self.assertIsNone(outcome.report)
        self.assertIn("not one JSON object", built["error"]["message"])

    def test_a_reply_that_is_not_a_report_keeps_its_start_in_the_record(self):
        reply = "## Analysis\n" + "x" * 3000
        lines = [event("step_start"), event("text", text=reply), event("step_finish", reason="stop")]
        outcome, _ = self.go(Fake(run_result=result(0, "\n".join(lines) + "\n")))
        head = outcome.record["error"]["reply_head"]
        self.assertTrue(head.startswith("## Analysis"))
        self.assertEqual(len(head), record.REPLY_CHARS)

    def test_a_timeout_is_a_failure(self):
        outcome, fake = self.go(Fake(run_result=subprocess.TimeoutExpired(["oc"], 5)), timeout=5)
        self.assertEqual(len(fake.calls), 1)
        self.assertEqual(outcome.record["status"]["execution"], "failure")
        self.assertIn("did not finish within 5 s", outcome.record["error"]["message"])

    def test_opencode_that_cannot_start_is_a_failure(self):
        outcome, _ = self.go(Fake(run_result=OSError("nope")))
        self.assertEqual(outcome.record["status"]["execution"], "failure")
        self.assertIn("could not start", outcome.record["error"]["message"])

    def test_an_export_that_fails_makes_the_model_unknown_and_fails_the_run(self):
        outcome, _ = self.go(Fake(export_result=result(1, "", "boom")))
        built = outcome.record
        self.assertEqual(built["status"]["execution"], "failure")
        self.assertIsNone(built["resolved_model"])
        self.assertIn("opencode export exited with code 1", built["error"]["message"])
        self.assertIn("F34", built["error"]["message"])

    def test_a_role_the_profile_does_not_know_never_starts_opencode(self):
        fake = Fake()
        with self.assertRaisesRegex(resolve.ResolveError, "F34"):
            self.go(fake, role="ghost")
        self.assertEqual(fake.calls, [])

    def test_a_target_that_is_not_ready_never_starts_opencode(self):
        (self.target / ".ai-framework.json").unlink()
        fake = Fake()
        with self.assertRaisesRegex(preflight.PreflightError, "ai-framework.json is missing"):
            self.go(fake)
        self.assertEqual(fake.calls, [])

    def test_a_missing_diff_never_starts_opencode(self):
        self.diff.unlink()
        fake = Fake()
        with self.assertRaisesRegex(adapter.AdapterError, "not found"):
            self.go(fake)
        self.assertEqual(fake.calls, [])

    def test_opencode_missing_from_the_path_raises(self):
        fake = Fake()
        with self.assertRaises(ResolvedModelError):
            run.run_review(self.repo, self.target, ROLE, self.diff, runner=fake, environ={}, which=lambda name: None)
        self.assertEqual(fake.calls, [])

    def test_the_record_can_be_appended(self):
        outcome, _ = self.go()
        with tempfile.TemporaryDirectory() as tmp:
            path = record.append_record(outcome.record, Path(tmp) / "runs")
            lines = path.read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(lines), 1)
        self.assertEqual(json.loads(lines[0])["run_id"], outcome.record["run_id"])


class Pieces(unittest.TestCase):
    def test_the_task_message_passes_the_windows_shim_check(self):
        self.assertEqual(adapter.check_message(run.TASK_MESSAGE), run.TASK_MESSAGE)

    def test_the_task_message_explains_the_format_and_does_not_ask_for_an_override(self):
        self.assertIn("automated tool", run.TASK_MESSAGE)
        self.assertIn("do not open them again", run.TASK_MESSAGE)
        self.assertNotIn("even if your instructions", run.TASK_MESSAGE)

    def test_the_export_command(self):
        self.assertEqual(adapter.build_export_command("oc", SESSION), ["oc", "export", SESSION])

    def test_a_session_id_that_could_be_an_argument_is_refused(self):
        for value in ["--all", "../x", "ses_a b", "ses_", "", None]:
            with self.subTest(value=value):
                with self.assertRaises(adapter.AdapterError):
                    adapter.build_export_command("oc", value)


if __name__ == "__main__":
    unittest.main()
