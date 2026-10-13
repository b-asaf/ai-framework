import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tools"))

import validate_framework  # noqa: E402


class FastLane(unittest.TestCase):
    """Guards for DEC-018: the developer declares the fast lane, code measures it, every gate still runs."""

    def read(self, relative):
        return (REPO / relative).read_text(encoding="utf-8-sig")

    def test_the_command_points_at_the_orchestrator(self):
        text = self.read("commands/quick.md")
        self.assertIn("agent: orchestrator", text)
        self.assertIn("$ARGUMENTS", text)
        self.assertIn("Invoked via `/quick`", text)

    def test_only_the_developer_can_declare_the_lane(self):
        text = self.read("agents/orchestrator.md")
        self.assertIn("never choose this lane yourself", text)
        self.assertIn("never trim the change to fit", text)
        self.assertLess(text.index("## Invoked via `/quick`"), text.index("## On every task"))

    def test_the_orchestrator_may_run_the_measuring_script(self):
        bash = validate_framework.load_agent(REPO / "agents" / "orchestrator.md").permission["bash"]
        self.assertEqual(bash.get("python *scripts*quick-lane-check.py*"), "allow")
        self.assertEqual(bash.get("python3 *scripts*quick-lane-check.py*"), "allow")

    def test_the_gatekeeper_knows_the_lane(self):
        text = self.read("agents/gatekeeper.md")
        self.assertIn("Lane: quick", text)
        self.assertIn("quick-lane-check", text)

    def test_agents_md_names_the_lane(self):
        self.assertIn("/quick", self.read("AGENTS.md"))


if __name__ == "__main__":
    unittest.main()
