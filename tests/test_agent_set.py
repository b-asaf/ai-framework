"""Guards for DEC-028 (S.4, S.5, S.12f): the six implementers stay in step, no skill is orphaned, the stack file has one name."""

import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
IMPLEMENTERS = ("api", "backend", "db", "frontend", "frontend-error-fixer", "ui")
TEXT_FOLDERS = ("agents", "commands", "instructions", "skills")
OLD_STACK = "project-overview/sub/stack.md"


def read(path):
    return path.read_text(encoding="utf-8-sig", errors="replace")


def ask_rules(agent):
    front = read(REPO / "agents" / f"{agent}.md").split("---")[1]
    return [line.strip() for line in front.splitlines() if line.rstrip().endswith(": ask")]


def skill_folders():
    return sorted(path for path in (REPO / "skills").iterdir() if path.is_dir())


def instruction_texts():
    texts = {"AGENTS.md": read(REPO / "AGENTS.md"), "README.md": read(REPO / "README.md")}
    for folder in TEXT_FOLDERS:
        for path in sorted((REPO / folder).rglob("*.md")):
            texts[path.relative_to(REPO).as_posix()] = read(path)
    return texts


class ImplementerDrift(unittest.TestCase):
    def test_the_six_share_the_same_ask_rules(self):
        first = ask_rules("backend")
        self.assertTrue(first)
        for agent in IMPLEMENTERS:
            with self.subTest(agent=agent):
                self.assertEqual(ask_rules(agent), first)

    def test_every_implementer_loads_build_verify(self):
        for agent in IMPLEMENTERS:
            with self.subTest(agent=agent):
                self.assertIn("- `build-verify`", read(REPO / "agents" / f"{agent}.md"))


class SkillSet(unittest.TestCase):
    def test_every_skill_folder_has_a_skill_file_or_is_the_routing_data(self):
        """skill-routing holds skill-rules.json, which agents read (AGENTS.md rule 8); every other folder holds a SKILL.md."""
        for folder in skill_folders():
            with self.subTest(skill=folder.name):
                if folder.name == "skill-routing":
                    self.assertTrue((folder / "skill-rules.json").is_file())
                else:
                    self.assertTrue((folder / "SKILL.md").is_file())

    def test_every_skill_is_named_outside_its_own_folder(self):
        texts = instruction_texts()
        for folder in skill_folders():
            name = folder.name
            pattern = re.compile(r"(?<![\w-])" + re.escape(name) + r"(?![\w-])")
            own = f"skills/{name}/"
            named = [path for path, text in texts.items() if not path.startswith(own) and pattern.search(text)]
            with self.subTest(skill=name):
                self.assertTrue(named, f"{name} is named by no agent, command, skill, instruction file, AGENTS.md or README")


class StackFileName(unittest.TestCase):
    def test_nothing_names_the_old_spelling(self):
        found = [path for path, text in instruction_texts().items() if OLD_STACK in text]
        self.assertEqual(found, [])

    def test_the_skill_template_has_the_flat_stack_file(self):
        self.assertTrue((REPO / "skills" / "project-overview" / "stack.md").is_file())
        self.assertFalse((REPO / "skills" / "project-overview" / "sub" / "stack.md").exists())


if __name__ == "__main__":
    unittest.main()
