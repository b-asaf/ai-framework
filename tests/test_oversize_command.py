"""Guards for DEC-025 (S.6c): the developer declares /oversize, no agent offers it, the script is allowed."""

import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tools"))

import validate_framework  # noqa: E402

SECTION_START = "## Invoked via `/oversize`"
SECTION_END = "## On every task"
RULES = (
    "never offer it",
    "Never invent one",
    "Never rewrite history",
    "never rounded",
    "empty commit",
    "Diff-Size-Approved: <lines> <reason>",
)


class OversizeCommand(unittest.TestCase):
    def read(self, relative):
        return (REPO / relative).read_text(encoding="utf-8-sig")

    def orchestrator_parts(self):
        text = self.read("agents/orchestrator.md")
        start, end = text.index(SECTION_START), text.index(SECTION_END)
        self.assertLess(start, end)
        return text[start:end], text[:start] + text[end:]

    def test_the_command_points_at_the_orchestrator(self):
        text = self.read("commands/oversize.md")
        self.assertIn("agent: orchestrator", text)
        self.assertIn("$ARGUMENTS", text)
        self.assertIn("Invoked via `/oversize`", text)

    def test_the_orchestrator_section_holds_the_rules(self):
        section, _outside = self.orchestrator_parts()
        for rule in RULES:
            with self.subTest(rule=rule):
                self.assertIn(rule, section)

    def test_only_the_oversize_section_names_the_command_or_the_line(self):
        _section, outside = self.orchestrator_parts()
        texts = {"agents/orchestrator.md (outside its section)": outside}
        for path in sorted((REPO / "agents").glob("*.md")):
            if path.name != "orchestrator.md":
                texts[f"agents/{path.name}"] = path.read_text(encoding="utf-8-sig")
        for relative in ("AGENTS.md", "skills/pr-provider/SKILL.md"):
            texts[relative] = self.read(relative)
        for label, text in texts.items():
            with self.subTest(file=label):
                self.assertNotIn("/oversize", text)
                self.assertNotIn("Diff-Size-Approved", text)

    def test_the_atomic_changes_skill_never_names_the_command(self):
        text = self.read("skills/atomic-changes/SKILL.md")
        self.assertNotIn("/oversize", text)
        self.assertIn("never writes this line on its own", text)

    def test_the_orchestrator_may_run_the_measuring_script(self):
        bash = validate_framework.load_agent(REPO / "agents" / "orchestrator.md").permission["bash"]
        self.assertEqual(bash.get("python *scripts*diff-size-check.py*"), "allow")
        self.assertEqual(bash.get("python3 *scripts*diff-size-check.py*"), "allow")

    def test_the_readme_lists_the_command_and_the_script(self):
        text = self.read("README.md")
        self.assertIn("| `/oversize`", text)
        self.assertIn("diff-size-check.py", text)
        self.assertIn("Diff-Size-Approved", text)


if __name__ == "__main__":
    unittest.main()
