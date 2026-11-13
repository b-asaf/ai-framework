import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from execution.runner import opencode_adapter as adapter  # noqa: E402

REVIEWER = (
    "---\n"
    "description: Fixture reviewer\n"
    "mode: subagent\n"
    "permission:\n"
    "  bash:\n"
    '    "*": ask\n'
    '    "git *": deny\n'
    '    "git status": allow\n'
    "  external_directory:\n"
    "    'D:\\\\ref\\\\*': allow\n"
    "  edit: deny\n"
    "---\n"
    "Body.\n"
    '    "*": ask\n'
)
NO_MAP = "---\ndescription: x\nmode: subagent\npermission:\n  edit: deny\n---\nBody.\n"


class DenyUnanswerableAsks(unittest.TestCase):
    def test_the_bash_catch_all_becomes_a_deny_and_the_other_rules_stay(self):
        out = adapter.deny_unanswerable_asks(REVIEWER)
        self.assertIn('  bash:\n    "*": deny\n    "git *": deny\n    "git status": allow\n', out)

    def test_external_directory_gets_a_deny_before_its_allow(self):
        out = adapter.deny_unanswerable_asks(REVIEWER)
        self.assertIn("  external_directory:\n    \"*\": deny\n    'D:\\\\ref\\\\*': allow\n", out)

    def test_a_missing_external_directory_map_is_added_under_permission(self):
        expected = "---\ndescription: x\nmode: subagent\npermission:\n  external_directory:\n    \"*\": deny\n  edit: deny\n---\nBody.\n"
        self.assertEqual(adapter.deny_unanswerable_asks(NO_MAP), expected)

    def test_the_body_is_not_touched(self):
        self.assertTrue(adapter.deny_unanswerable_asks(REVIEWER).endswith('---\nBody.\n    "*": ask\n'))

    def test_an_external_directory_that_is_not_a_map_is_left_alone(self):
        agent = "---\nmode: subagent\npermission:\n  external_directory: allow\n---\nBody.\n"
        self.assertEqual(adapter.deny_unanswerable_asks(agent), agent)

    def test_a_file_without_permission_is_unchanged(self):
        agent = "---\nmode: subagent\n---\nBody.\n"
        self.assertEqual(adapter.deny_unanswerable_asks(agent), agent)

    def test_line_endings_are_kept(self):
        crlf = adapter.deny_unanswerable_asks(REVIEWER.replace("\n", "\r\n"))
        self.assertEqual(crlf, adapter.deny_unanswerable_asks(REVIEWER).replace("\n", "\r\n"))
        self.assertNotIn("\r\r", crlf)

    def test_the_real_agents_have_no_catch_all_ask_left(self):
        for role in ("code-reviewer", "qa"):
            with self.subTest(role=role):
                text = adapter.load_agent_text(REPO, role).replace("\r\n", "\n")
                head = adapter.deny_unanswerable_asks(text).split("\n---\n")[0]
                self.assertIn('  bash:\n    "*": deny\n', head)
                self.assertIn('  external_directory:\n    "*": deny\n', head)
                self.assertNotIn('"*": ask', head)

    def test_prepare_run_dir_writes_the_headless_agent(self):
        with tempfile.TemporaryDirectory() as tmp:
            setup = adapter.prepare_run_dir(tmp, "qa", REVIEWER, "m/one")
            written = (setup.config_dir / "agents" / "qa.md").read_bytes().decode("utf-8")
        self.assertEqual(written, adapter.deny_unanswerable_asks(adapter.derive_agent(REVIEWER)))
        self.assertIn('  bash:\n    "*": deny\n', written)


if __name__ == "__main__":
    unittest.main()
