"""The gatekeeper checklist holds judgment items only: facts that code decides at push are not on it (DEC-015, 3A.4)."""

import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PREFIXES = ("feat/", "fix/", "chore/", "refactor/", "docs/", "hotfix/", "release/")


class GatekeeperScope(unittest.TestCase):
    def setUp(self):
        self.text = (REPO / "agents" / "gatekeeper.md").read_text(encoding="utf-8-sig")
        self.items = [line for line in self.text.splitlines() if line.startswith("- [ ]")]

    def has_item(self, fragment):
        return any(fragment in item for item in self.items)

    def test_facts_that_code_decides_at_push_are_not_checklist_items(self):
        for fragment in (
            "unapproved dependency",
            "without documented developer approval",
            "`main` or `master`",
            "zero failures",
            "zero violations on all tools",
            "Gatekeeper is read-only aside",
        ):
            with self.subTest(fragment=fragment):
                self.assertFalse(self.has_item(fragment))

    def test_the_branch_prefix_item_lists_all_seven_prefixes(self):
        item = next(line for line in self.items if "correct prefix" in line)
        for prefix in PREFIXES:
            with self.subTest(prefix=prefix):
                self.assertIn("`" + prefix + "`", item)

    def test_the_static_analysis_coverage_and_xray_items_stay(self):
        for fragment in ("lizard", "coverage precheck", "Xray"):
            with self.subTest(fragment=fragment):
                self.assertTrue(self.has_item(fragment))

    def test_the_code_decided_section_points_at_the_push_gate(self):
        self.assertIn("Decided in code, not on this checklist", self.text)
        self.assertIn("pr-provider", self.text)


if __name__ == "__main__":
    unittest.main()
