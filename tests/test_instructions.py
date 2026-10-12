import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

IMPLEMENTERS = ["api", "backend", "db", "frontend", "frontend-error-fixer", "ui"]


class Instructions(unittest.TestCase):
    """Guards for DEC-017: two approval checkpoints, then autonomy. They check wording, so they are blunt on purpose."""

    def read(self, relative):
        return (REPO / relative).read_text(encoding="utf-8-sig")

    def test_agents_md_has_no_blanket_plan_confirmation(self):
        text = self.read("AGENTS.md")
        self.assertNotIn("Always show a plan and get confirmation before writing files", text)
        self.assertIn("two checkpoints", text)

    def test_agents_md_asks_about_the_branch_only_off_the_base_branch(self):
        text = self.read("AGENTS.md")
        self.assertIn("On the base branch", text)
        self.assertIn("On any other branch", text)

    def test_implementers_do_not_ask_the_developer_for_confirmations_or_branches(self):
        for name in IMPLEMENTERS:
            text = self.read("agents/" + name + ".md")
            with self.subTest(agent=name):
                self.assertNotIn("and wait for confirmation", text)
                self.assertNotIn("ask the developer if unsure", text)
                self.assertNotIn("Please run: `git checkout -b", text)

    def test_orchestrator_checks_the_branch_before_the_product_manager(self):
        text = self.read("agents/orchestrator.md")
        self.assertIn("Branch check first", text)
        self.assertLess(text.index("Branch check first"), text.index("Route to `@product-manager`"))

    def test_orchestrator_asks_where_the_next_pr_branch_starts(self):
        self.assertIn("Its branch will start from", self.read("agents/orchestrator.md"))


if __name__ == "__main__":
    unittest.main()
