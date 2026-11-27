import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
GRAPH = 'python "$HOME/.config/opencode/scripts/graph.py"'


class CodeGraphText(unittest.TestCase):
    """DEC-030: the framework runs graphify through scripts/graph.py, and the skill has its own name."""

    def read(self, relative):
        return (REPO / relative).read_text(encoding="utf-8-sig")

    def test_the_skill_has_its_own_name_and_the_commands(self):
        text = self.read("skills/code-graph/SKILL.md")
        self.assertTrue(text.startswith("---\nname: code-graph\n"))
        self.assertIn("## Quick reference", text)
        for command in ("query", "path", "explain", "update", "build"):
            with self.subTest(command=command):
                self.assertIn(f"{GRAPH} {command}", text)

    def test_the_skill_forbids_running_graphify_directly(self):
        text = self.read("skills/code-graph/SKILL.md")
        for fragment in ("Never run graphify yourself", "graphify install", "graphify hook install"):
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, text)

    def test_no_framework_skill_is_named_graphify(self):
        self.assertFalse((REPO / "skills" / "graphify").exists())

    def test_first_run_builds_the_graph(self):
        text = self.read("skills/first-run-analysis/SKILL.md")
        self.assertIn("## Step 3d", text)
        self.assertIn(f"{GRAPH} build", text)

    def test_the_orchestrator_updates_the_graph(self):
        self.assertIn(f"{GRAPH} update", self.read("agents/orchestrator.md"))


if __name__ == "__main__":
    unittest.main()
