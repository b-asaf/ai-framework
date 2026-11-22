import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from execution.runner import preflight  # noqa: E402

STACK_OK = "# Stack\n\n- Language: JavaScript\n"


def write(root, relative, text):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def model_config(role="qa"):
    return json.dumps({"agent": {role: {"model": "m/one"}}})


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        write(self.root, ".ai-framework/project-overview/stack.md", STACK_OK)
        write(self.root, ".ai-framework.json", "{}")

    def check(self, role="qa", environ=None):
        return preflight.check_target(self.root, role, {} if environ is None else environ)

    def joined(self, **kwargs):
        return " | ".join(self.check(**kwargs))


class Target(Base):
    def test_a_ready_target_is_clean(self):
        self.assertEqual(self.check(), [])

    def test_a_target_that_is_not_a_folder_is_flagged(self):
        problems = preflight.check_target(self.root / "nope", "qa", {})
        self.assertEqual(len(problems), 1)
        self.assertIn("not a folder", problems[0])

    def test_a_missing_stack_file_is_flagged(self):
        (self.root / ".ai-framework" / "project-overview" / "stack.md").unlink()
        self.assertIn("stack.md is missing", self.joined())

    def test_a_stack_file_with_only_headings_is_flagged(self):
        for text in ("", "# Stack\n", "# Stack\n\n  \n## Build\n"):
            with self.subTest(text=text):
                write(self.root, ".ai-framework/project-overview/stack.md", text)
                self.assertIn("no content beyond headings", self.joined())

    def test_a_stack_file_with_the_placeholder_is_flagged(self):
        write(self.root, ".ai-framework/project-overview/stack.md", "# Stack\n- Language: [XXX]\n")
        self.assertIn("[XXX]", self.joined())

    def test_a_missing_framework_config_is_flagged(self):
        (self.root / ".ai-framework.json").unlink()
        self.assertIn(".ai-framework.json is missing", self.joined())

    def test_a_framework_config_that_is_not_a_json_object_is_flagged(self):
        for text, message in (("{bad", "cannot be read"), ("[]", "must be a JSON object")):
            with self.subTest(text=text):
                write(self.root, ".ai-framework.json", text)
                self.assertIn(message, self.joined())

    def test_an_agent_model_in_the_project_config_is_flagged(self):
        write(self.root, "opencode.json", model_config())
        self.assertIn("opencode.json sets agent.qa.model", self.joined())

    def test_an_agent_model_in_the_dot_opencode_config_is_flagged(self):
        write(self.root, ".opencode/opencode.json", model_config("other"))
        text = self.joined()
        self.assertIn(".opencode/opencode.json sets agent.other.model", text)

    def test_a_project_config_without_an_agent_model_is_clean(self):
        write(self.root, "opencode.json", json.dumps({"agent": {"qa": {"temperature": 0.1}}, "permission": {}}))
        write(self.root, ".opencode/opencode.json", json.dumps({"$schema": "x"}))
        self.assertEqual(self.check(), [])

    def test_a_project_config_that_cannot_be_read_is_flagged(self):
        write(self.root, "opencode.json", "{bad")
        self.assertIn("opencode.json cannot be read", self.joined())

    def test_a_jsonc_config_is_flagged_because_it_cannot_be_checked(self):
        write(self.root, "opencode.jsonc", "{}")
        self.assertIn("cannot be checked", self.joined())

    def test_a_project_agent_file_for_the_role_is_flagged(self):
        write(self.root, ".opencode/agents/qa.md", "---\nmode: subagent\n---\n")
        self.assertIn(".opencode/agents/qa.md", self.joined())

    def test_a_project_agent_file_for_another_role_is_not_flagged(self):
        write(self.root, ".opencode/agents/other.md", "---\nmode: subagent\n---\n")
        self.assertEqual(self.check(), [])

    def test_an_agent_model_in_the_opencode_config_file_is_flagged(self):
        write(self.root, "routing.json", model_config())
        environ = {"OPENCODE_CONFIG": str(self.root / "routing.json")}
        self.assertIn("OPENCODE_CONFIG file sets agent.qa.model", self.joined(environ=environ))

    def test_an_opencode_config_file_without_an_agent_model_is_clean(self):
        write(self.root, "routing.json", json.dumps({"$schema": "x"}))
        self.assertEqual(self.check(environ={"OPENCODE_CONFIG": str(self.root / "routing.json")}), [])

    def test_every_problem_is_reported_together(self):
        (self.root / ".ai-framework" / "project-overview" / "stack.md").unlink()
        (self.root / ".ai-framework.json").unlink()
        write(self.root, "opencode.json", model_config())
        self.assertEqual(len(self.check()), 3)

    def test_require_raises_with_every_problem_listed(self):
        (self.root / ".ai-framework.json").unlink()
        write(self.root, "opencode.json", model_config())
        with self.assertRaises(preflight.PreflightError) as caught:
            preflight.require(self.root, "qa", {})
        text = str(caught.exception)
        self.assertIn("not ready", text)
        self.assertIn(".ai-framework.json is missing", text)
        self.assertIn("agent.qa.model", text)

    def test_require_returns_quietly_for_a_ready_target(self):
        self.assertIsNone(preflight.require(self.root, "qa", {}))


class GeneratedFolder(Base):
    """The stack file is looked for in the folder for generated files (DEC-026)."""

    def test_a_changed_folder_is_used(self):
        (self.root / ".ai-framework" / "project-overview" / "stack.md").unlink()
        write(self.root, ".ai-framework.json", json.dumps({"generatedDir": "docs/ai"}))
        self.assertIn("docs/ai/project-overview/stack.md is missing", self.joined())
        write(self.root, "docs/ai/project-overview/stack.md", STACK_OK)
        self.assertEqual(self.check(), [])

    def test_files_only_under_the_old_place_are_not_found_and_the_message_names_the_path(self):
        (self.root / ".ai-framework" / "project-overview" / "stack.md").unlink()
        write(self.root, "docs/project-overview/stack.md", STACK_OK)
        self.assertIn(".ai-framework/project-overview/stack.md is missing", self.joined())

    def test_a_refused_folder_is_one_problem_and_no_stack_check(self):
        for value in ("../x", "/abs", "docs\\ai", "a&b", 5):
            with self.subTest(value=value):
                write(self.root, ".ai-framework.json", json.dumps({"generatedDir": value}))
                problems = self.check()
                self.assertEqual(len(problems), 1)
                self.assertIn("generatedDir", problems[0])

    def test_a_config_that_cannot_be_read_is_reported_once(self):
        write(self.root, ".ai-framework.json", "{bad")
        problems = self.check()
        self.assertEqual(len([problem for problem in problems if "cannot be read" in problem]), 1)


if __name__ == "__main__":
    unittest.main()
