import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tools"))

from execution.runner import opencode_adapter as adapter  # noqa: E402
from lib.routing import load_profile, profile_models  # noqa: E402

PROFILE = REPO / "execution" / "profiles" / "default.json"
ROUTING = REPO / "execution" / "routing.json"
AGENT = (
    "---\n"
    "description: Fixture agent\n"
    "mode: subagent\n"
    "permission:\n"
    "  mode: deny\n"
    "  edit: deny\n"
    "---\n"
    "Body line.\n"
    "mode: subagent\n"
)
OLD_MODE = "description: Fixture agent\nmode: subagent\n"
NEW_MODE = "description: Fixture agent\nmode: primary\n"


class DeriveAgent(unittest.TestCase):
    def test_only_the_top_level_mode_line_changes(self):
        self.assertEqual(adapter.derive_agent(AGENT), AGENT.replace(OLD_MODE, NEW_MODE))

    def test_an_agent_that_is_already_primary_is_unchanged(self):
        primary = AGENT.replace(OLD_MODE, NEW_MODE)
        self.assertEqual(adapter.derive_agent(primary), primary)

    def test_line_endings_are_kept(self):
        crlf = AGENT.replace("\n", "\r\n")
        expected = crlf.replace(OLD_MODE.replace("\n", "\r\n"), NEW_MODE.replace("\n", "\r\n"))
        self.assertEqual(adapter.derive_agent(crlf), expected)

    def test_the_body_and_nested_keys_are_not_touched(self):
        derived = adapter.derive_agent(AGENT)
        self.assertTrue(derived.endswith("Body line.\nmode: subagent\n"))
        self.assertIn("\n  mode: deny\n", derived)

    def test_no_model_line_is_added(self):
        self.assertNotIn("model:", adapter.derive_agent(AGENT))

    def test_a_byte_order_mark_is_kept(self):
        self.assertTrue(adapter.derive_agent("\ufeff" + AGENT).startswith("\ufeff---\n"))

    def test_a_file_that_cannot_be_derived_is_refused(self):
        cases = [
            ("no frontmatter\n", "no frontmatter"),
            ("---\nmode: subagent\n", "not closed"),
            ("---\ndescription: x\n---\n", "exactly one"),
            ("---\nmode: a\nmode: b\n---\n", "exactly one"),
            ("---\nmode: subagent\nmodel: m/one\n---\n", "DEC-019"),
        ]
        for text, message in cases:
            with self.subTest(text=text):
                with self.assertRaisesRegex(adapter.AdapterError, message):
                    adapter.derive_agent(text)

    def test_every_real_agent_derives_with_one_changed_line_at_most(self):
        for path in sorted((REPO / "agents").glob("*.md")):
            with self.subTest(agent=path.stem):
                original = path.read_bytes().decode("utf-8")
                old = original.splitlines(keepends=True)
                new = adapter.derive_agent(original).splitlines(keepends=True)
                self.assertEqual(len(old), len(new))
                self.assertLessEqual(len([1 for a, b in zip(old, new) if a != b]), 1)
                self.assertIn("mode: primary", [line.rstrip("\r\n") for line in new])


class Command(unittest.TestCase):
    def test_a_plain_message_is_accepted(self):
        self.assertEqual(adapter.check_message("Review the attached diff"), "Review the attached diff")

    def test_text_that_breaks_the_windows_shim_is_refused(self):
        for message in ['say "hi"', "it's", "a | b", "{x}", "two\nlines", "a & b", "100%", "", "   ", None]:
            with self.subTest(message=message):
                with self.assertRaises(adapter.AdapterError):
                    adapter.check_message(message)

    def test_the_command_puts_the_message_before_the_files(self):
        command = adapter.build_command("oc", "qa", "Review the diff", [Path("a") / "task.md", Path("a") / "b.patch"])
        self.assertEqual(
            command,
            ["oc", "run", "Review the diff", "--agent", "qa", "--format", "json", "-f", "a/task.md", "-f", "a/b.patch"],
        )

    def test_an_agent_name_that_is_a_path_is_refused(self):
        with self.assertRaisesRegex(adapter.AdapterError, "agent name"):
            adapter.build_command("oc", "../x", "message", [])


class Environment(unittest.TestCase):
    def test_both_variables_are_set_on_a_copy(self):
        base = {"PATH": "p", "OPENCODE_CONFIG": "old"}
        environment = adapter.build_environment(base, Path("t") / "run-routing.json", Path("t") / "cfg")
        self.assertEqual(environment["PATH"], "p")
        self.assertEqual(environment["OPENCODE_CONFIG"], "t/run-routing.json")
        self.assertEqual(environment["OPENCODE_CONFIG_DIR"], "t/cfg")
        self.assertEqual(base, {"PATH": "p", "OPENCODE_CONFIG": "old"})


class RenderRunConfig(unittest.TestCase):
    def test_one_role(self):
        text = adapter.render_run_config({"qa": "m/one"})
        self.assertEqual(json.loads(text), {"$schema": adapter.SCHEMA_URL, "agent": {"qa": {"model": "m/one"}}})
        self.assertTrue(text.endswith("\n"))
        self.assertTrue(text.splitlines()[1].strip().startswith('"$schema"'))

    def test_the_real_profile_renders_the_committed_routing_file(self):
        text = adapter.render_run_config(profile_models(load_profile(PROFILE)))
        self.assertEqual(text, ROUTING.read_bytes().decode("utf-8"))

    def test_nothing_or_a_blank_model_is_refused(self):
        for models in ({}, {"qa": ""}, {"qa": None}):
            with self.subTest(models=models):
                with self.assertRaises(adapter.AdapterError):
                    adapter.render_run_config(models)


class PrepareRunDir(unittest.TestCase):
    def test_a_derived_agent_and_the_routing_are_written(self):
        with tempfile.TemporaryDirectory() as tmp:
            setup = adapter.prepare_run_dir(tmp, "qa", AGENT, "m/one")
            agent_file = setup.config_dir / "agents" / "qa.md"
            self.assertEqual(agent_file.read_bytes().decode("utf-8"), adapter.derive_agent(AGENT))
            routing = json.loads(setup.config_file.read_text(encoding="utf-8"))
            self.assertEqual(routing["agent"], {"qa": {"model": "m/one"}})
            self.assertEqual(setup.config_file.parent, Path(tmp))
            self.assertNotIn(setup.config_dir, setup.config_file.parents)

    def test_line_endings_are_kept_on_disk(self):
        with tempfile.TemporaryDirectory() as tmp:
            setup = adapter.prepare_run_dir(tmp, "qa", AGENT.replace("\n", "\r\n"), "m/one")
            data = (setup.config_dir / "agents" / "qa.md").read_bytes()
        self.assertIn(b"\r\n", data)
        self.assertNotIn(b"\r\r\n", data)

    def test_bad_input_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            for role, text, model in [("../x", AGENT, "m/one"), ("qa", "no frontmatter\n", "m/one"), ("qa", AGENT, "")]:
                with self.subTest(role=role, model=model):
                    with self.assertRaises(adapter.AdapterError):
                        adapter.prepare_run_dir(tmp, role, text, model)
            self.assertEqual(list(Path(tmp).iterdir()), [])


class LoadAgentText(unittest.TestCase):
    def test_a_real_agent_is_read_and_can_be_derived(self):
        text = adapter.load_agent_text(REPO, "code-reviewer")
        self.assertTrue(text.startswith("---"))
        self.assertIn("mode: primary", adapter.derive_agent(text))

    def test_a_missing_agent_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(adapter.AdapterError, "cannot be read"):
                adapter.load_agent_text(tmp, "qa")

    def test_a_name_that_is_a_path_is_refused(self):
        with self.assertRaisesRegex(adapter.AdapterError, "agent name"):
            adapter.load_agent_text(REPO, "../x")


if __name__ == "__main__":
    unittest.main()
