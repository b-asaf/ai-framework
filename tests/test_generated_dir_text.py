"""Guards for DEC-026 (S.12d): agents and skills find the generated-files folder through one rule."""

import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCANNED = ("agents", "commands", "skills", "instructions")
OLD_PATHS = ("docs/project-overview", "docs/refactoring-plan")
WRITERS = (
    "commands/first-run.md",
    "agents/refactor-planner.md",
    "skills/improve-codebase-architecture/SKILL.md",
)


class GeneratedFolderText(unittest.TestCase):
    def read(self, relative):
        return (REPO / relative).read_text(encoding="utf-8-sig")

    def block(self, opening, closing):
        text = self.read("AGENTS.md")
        start = text.index(opening)
        return text[start:text.index(closing, start)]

    def test_check_one_says_how_to_find_the_folder(self):
        check = self.block('<check id="1"', "</check>")
        for fragment in ("generatedDir", ".ai-framework/", "project-overview/stack.md", "stop and tell the developer"):
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, check)

    def test_rule_four_points_to_check_one_and_not_to_a_path(self):
        rule = self.block('<rule id="4"', "</rule>")
        self.assertIn("Check 1", rule)
        self.assertNotIn("docs/project-overview", rule)

    def test_no_instruction_file_names_the_old_paths(self):
        paths = [REPO / "AGENTS.md"]
        for folder in SCANNED:
            paths += sorted((REPO / folder).rglob("*.md"))
        found = [
            f"{path.relative_to(REPO).as_posix()}: {old}"
            for path in paths
            for old in OLD_PATHS
            if old in path.read_text(encoding="utf-8-sig")
        ]
        self.assertEqual(found, [])

    def test_first_run_uses_the_folder_and_no_longer_writes_manual_md(self):
        text = self.read("skills/first-run-analysis/SKILL.md")
        self.assertIn("<generated folder>/project-overview/", text)
        self.assertIn("generatedDir", text)
        self.assertNotIn("Manual.md", text)

    def test_the_other_writers_name_the_folder_rule(self):
        for relative in WRITERS:
            with self.subTest(file=relative):
                text = self.read(relative)
                self.assertIn("generatedDir", text)
                self.assertIn("Check 1", text)


if __name__ == "__main__":
    unittest.main()
