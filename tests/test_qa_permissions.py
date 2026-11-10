"""The real agents/qa.md keeps an edit rule that lets it write tests and nothing else (F75).

A plain `edit: deny` leaves the agent without any file-writing tool, and the `write` key has no effect.
lint_read_only skips an agent whose edit is a map, so these tests also hold the task deny.
"""

import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tools"))

import validate_framework  # noqa: E402


class QaPermissions(unittest.TestCase):
    def setUp(self):
        self.permission = validate_framework.load_agent(REPO / "agents" / "qa.md").permission

    def test_edit_denies_everything_first_and_then_allows_only_test_paths(self):
        edit = self.permission.get("edit")
        self.assertIsInstance(edit, dict)
        rules = list(edit.items())
        self.assertEqual(rules[0], ("*", "deny"))
        self.assertGreater(len(rules), 1)
        self.assertEqual({action for _, action in rules[1:]}, {"allow"})

    def test_every_allowed_edit_path_is_a_test_path(self):
        for pattern in list(self.permission["edit"])[1:]:
            self.assertRegex(pattern, r"test|spec")

    def test_delegation_stays_denied(self):
        self.assertEqual(self.permission.get("task"), "deny")


if __name__ == "__main__":
    unittest.main()
