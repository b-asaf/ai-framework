import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


class FirstRunGateWording(unittest.TestCase):
    """DEC-029: first-run asks for the base branch, and lint, format and test may each be empty."""

    def read(self, relative):
        return (REPO / relative).read_text(encoding="utf-8-sig")

    def test_first_run_asks_for_the_base_branch(self):
        text = self.read("skills/first-run-analysis/SKILL.md")
        for fragment in ("## Step 3c", "Which branch do your PRs target?", "git-context.py", "`BASE:`", "origin/<branch>"):
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, text)

    def test_first_run_says_every_command_may_be_empty_but_one(self):
        text = self.read("skills/first-run-analysis/SKILL.md")
        self.assertIn('{"lint": "<cmd or empty string>", "format": "<cmd or empty string>", "test": "<cmd or empty string>"}', text)
        self.assertIn("At least one of the three must be non-empty", text)
        self.assertNotIn('"test": "<cmd>"}', text)

    def test_the_stack_template_allows_none_configured_for_every_command(self):
        text = self.read("skills/project-overview/stack.md")
        self.assertEqual(text.count('or "none configured"'), 6)

    def test_build_verify_lets_a_project_leave_a_stage_empty(self):
        text = self.read("skills/build-verify/SKILL.md")
        self.assertIn("A stage left empty in `.ai-framework.json`", text)
        self.assertIn("each of which may be empty as long as one is not", text)

    def test_git_hooks_text_names_no_removed_hook(self):
        self.assertNotIn("Branch and commit rules enforced", self.read("skills/git-hooks/SKILL.md"))
        guide = self.read("skills/git-hooks/references/manager-installation.md")
        self.assertNotIn("check-branch", guide)
        self.assertNotIn(".git/hooks/pre-commit", guide)


if __name__ == "__main__":
    unittest.main()
