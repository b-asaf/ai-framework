"""Tests for a write role's run: the copy of the target, the facts stage and the workflow level
(plan step 3B.1). A fake subprocess stands in for OpenCode and for the test command."""

import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tools"))

from execution.runner import facts_stage, preflight, report, run, tree  # noqa: E402
from execution.runner import opencode_adapter as adapter  # noqa: E402

FIXTURES = REPO / "tests" / "fixtures" / "opencode-run"
ROLE = "qa"
MODEL = "github-copilot/claude-haiku-4.5"
AGENT = "---\ndescription: Fixture qa\nmode: subagent\npermission:\n  edit: deny\n  write: allow\n---\nWrite tests.\n"
EXPORT = (FIXTURES / "review-session.json").read_text(encoding="utf-8").replace("sample-reviewer", ROLE)
TEST_FILE = "src/clamp.test.ts"


def result(returncode=0, stdout=""):
    return SimpleNamespace(returncode=returncode, stdout=stdout, stderr="")


def event(kind, **part):
    return json.dumps({"type": kind, "sessionID": "ses_x", "part": part})


def put(root, relative, text):
    path = Path(root) / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.encode("utf-8"))
    return path


def qa_report(*files):
    return {
        "outcome": "TESTS_WRITTEN",
        "summary": "Tested clamp.",
        "frameworks": ["node:test"],
        "tests_written": [{"file": name, "count": 2, "covers": "clamp"} for name in files],
        "gaps": [],
        "production_issues": [],
    }


def make_repo(base):
    root = base / "repo"
    policy = {"version": 1, "models": {MODEL: {"family": "Claude", "status": "approved", "evaluation": None}}}
    put(root, "execution/policy.json", json.dumps(dict(policy, constraints={"independence": []})))
    put(root, "execution/profiles/default.json", json.dumps({"version": 1, "agents": {ROLE: {"model": MODEL}}}))
    put(root, f"agents/{ROLE}.md", AGENT)
    return root


def make_target(base, config):
    root = base / "target"
    put(root, "docs/project-overview/stack.md", "# Stack\n\n- Language: TypeScript\n")
    put(root, ".ai-framework.json", config)
    put(root, "src/clamp.ts", "export const clamp = 1;\n")
    os.chmod(put(root, ".git/objects/pack/one.idx", "x"), stat.S_IREAD)
    return root


class QaFake:
    """Stands in for subprocess.run: OpenCode writes files into its folder, then the tests run."""

    def __init__(self, reply, writes=None, tests=None):
        self.reply = reply
        self.writes = writes or {}
        self.tests = tests if tests is not None else result(0, "pass 2\n")
        self.calls = []
        self.seen = {}

    def __call__(self, command, **kwargs):
        self.calls.append((command, kwargs))
        if command[1] == "export":
            return result(0, EXPORT)
        if command[1] == "run":
            return self.opencode(command, Path(kwargs["cwd"]))
        self.seen["tests_cwd"] = Path(kwargs["cwd"])
        if isinstance(self.tests, Exception):
            raise self.tests
        return self.tests

    def opencode(self, command, cwd):
        self.seen["copy"] = cwd
        files = [command[i + 1] for i, argument in enumerate(command) if argument == "-f"]
        self.seen["task"] = Path(files[0]).read_text(encoding="utf-8")
        for name, text in self.writes.items():
            put(cwd, name, text)
        text = self.reply if isinstance(self.reply, str) else json.dumps(self.reply)
        lines = [event("step_start"), event("text", text=text), event("step_finish", reason="stop")]
        return result(0, "\n".join(lines))


class WritingRun(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base = Path(self.tmp.name)
        self.repo = make_repo(base)
        self.diff = put(base, "change.patch", "diff --git a/x b/x\n")
        self.target = make_target(base, json.dumps({"test": "mytests --all"}))

    def go(self, fake):
        return run.run_review(
            self.repo, self.target, ROLE, self.diff, runner=fake, environ={"PATH": "p"}, which=lambda name: "oc"
        )

    def test_a_good_run_ends_in_workflow_success(self):
        fake = QaFake(qa_report(TEST_FILE), {TEST_FILE: "t"})
        built = self.go(fake).record
        self.assertEqual(built["status"], {"execution": "success", "artifact": "success", "workflow": "success"})
        self.assertIsNone(built["error"])
        tests = built["verification"]["tests"]
        self.assertEqual((tests["command"], tests["exit_code"]), ("mytests --all", 0))
        self.assertEqual(built["verification"]["changed_files"]["added"], [TEST_FILE])
        self.assertEqual([call[0][1] for call in fake.calls], ["run", "export", "--all"])

    def test_the_real_target_is_never_touched_and_the_copy_is_removed(self):
        before = tree.snapshot(self.target)
        fake = QaFake(qa_report(TEST_FILE), {TEST_FILE: "t", "src/clamp.ts": "changed"})
        self.go(fake)
        copy = fake.seen["copy"]
        self.assertEqual(tree.snapshot(self.target), before)
        self.assertNotEqual(copy, self.target)
        self.assertEqual(fake.seen["tests_cwd"], copy)
        self.assertFalse(copy.exists())

    def test_failing_tests_are_a_workflow_failure(self):
        fake = QaFake(qa_report(TEST_FILE), {TEST_FILE: "t"}, tests=result(1, "not ok 1\n"))
        built = self.go(fake).record
        self.assertEqual(built["status"], {"execution": "success", "artifact": "success", "workflow": "failure"})
        self.assertIn("exit code 1", built["error"]["message"])
        self.assertEqual(built["verification"]["tests"]["tail"], ["not ok 1"])

    def test_a_report_that_disagrees_with_the_tree_is_a_workflow_failure(self):
        outcome = self.go(QaFake(qa_report(TEST_FILE), {}))
        problems = outcome.record["verification"]["problems"]
        self.assertEqual(outcome.record["status"]["workflow"], "failure")
        self.assertEqual(len(problems), 1)
        self.assertIn(TEST_FILE, problems[0])

    def test_a_changed_production_file_is_reported(self):
        writes = {TEST_FILE: "t", "src/clamp.ts": "changed"}
        outcome = self.go(QaFake(qa_report(TEST_FILE), writes))
        self.assertEqual(outcome.record["status"]["workflow"], "failure")
        problems = outcome.record["verification"]["problems"]
        self.assertEqual(problems, ["src/clamp.ts was modified but is not in tests_written"])

    def test_a_timeout_of_the_tests_is_a_workflow_failure(self):
        fake = QaFake(qa_report(TEST_FILE), {TEST_FILE: "t"}, tests=subprocess.TimeoutExpired("mytests", 1))
        outcome = self.go(fake)
        self.assertTrue(outcome.record["verification"]["tests"]["timed_out"])
        self.assertEqual(outcome.record["status"]["workflow"], "failure")

    def test_an_invalid_report_means_the_tests_do_not_run(self):
        fake = QaFake("I could not write tests")
        built = self.go(fake).record
        self.assertEqual(built["status"], {"execution": "success", "artifact": "failure", "workflow": "not_run"})
        self.assertIsNone(built["verification"])
        self.assertEqual([call[0][1] for call in fake.calls], ["run", "export"])

    def test_a_missing_or_unusable_test_command_never_starts_opencode(self):
        for config in ("{}", json.dumps({"test": "a && b"}), "not json"):
            with self.subTest(config=config):
                put(self.target, ".ai-framework.json", config)
                fake = QaFake(qa_report(TEST_FILE))
                with self.assertRaises(preflight.PreflightError):
                    self.go(fake)
                self.assertEqual(fake.calls, [])

    def test_the_qa_message_and_task_file_are_used(self):
        fake = QaFake(qa_report(TEST_FILE), {TEST_FILE: "t"})
        self.go(fake)
        self.assertEqual(fake.calls[0][0][2], run.QA_TASK_MESSAGE)
        self.assertEqual(fake.seen["task"], report.task_message("qa"))
        self.assertEqual(adapter.check_message(run.QA_TASK_MESSAGE), run.QA_TASK_MESSAGE)
        self.assertIs(run.TASK_MESSAGES["code-reviewer"], run.TASK_MESSAGE)

    def test_opencode_its_export_and_the_tests_start_without_the_shell_pwd(self):
        shell = {"PATH": "p", "PWD": "/d/ai-framework", "Pwd": "x"}
        fake = QaFake(qa_report(TEST_FILE), {TEST_FILE: "t"})
        run.run_review(self.repo, self.target, ROLE, self.diff, runner=fake, environ=shell, which=lambda name: "oc")
        self.assertEqual([call[0][1] for call in fake.calls], ["run", "export", "--all"])
        for _, kwargs in fake.calls:
            self.assertEqual([key for key in kwargs["env"] if key.upper() == "PWD"], [])
            self.assertEqual(kwargs["env"]["PATH"], "p")
        self.assertEqual(shell["PWD"], "/d/ai-framework")

    def test_the_clean_environment_drops_pwd_in_any_case_and_keeps_the_rest(self):
        self.assertEqual(run._clean_environment({"PWD": "a", "pwd": "b", "PATH": "p"}), {"PATH": "p"})


class FactsStage(unittest.TestCase):
    def test_prepare_returns_the_command_and_its_argv(self):
        with tempfile.TemporaryDirectory() as tmp:
            put(tmp, ".ai-framework.json", json.dumps({"test": "node --test"}))
            self.assertEqual(facts_stage.prepare(tmp), ("node --test", ["node", "--test"]))

    def test_a_test_command_that_is_not_found_is_a_failed_workflow(self):
        with tempfile.TemporaryDirectory() as tmp:
            level, verification, error = facts_stage.run_facts(
                "nope x", ["nope", "x"], tmp, tree.snapshot(tmp), [], which=lambda name: None
            )
        self.assertEqual(level, "failure")
        self.assertIn("not found", verification["tests"]["note"])
        self.assertIn("not found", error["message"])


if __name__ == "__main__":
    unittest.main()
