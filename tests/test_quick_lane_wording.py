import re
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tools"))

import validate_framework  # noqa: E402

OLD_NAME = re.compile(r"fast[ -]?lane")


def files_in(folders_and_patterns):
    found = []
    for folder, patterns in folders_and_patterns:
        for pattern in patterns:
            found += sorted((REPO / folder).rglob(pattern))
    return found


class QuickLane(unittest.TestCase):
    """Guards for DEC-018 and DEC-029: the developer declares the quick lane, code measures it, every gate still runs."""

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
        self.assertNotIn("quick-lane-check", text)

    def test_agents_md_names_the_lane(self):
        self.assertIn("/quick", self.read("AGENTS.md"))

    def test_the_lane_has_one_name_in_the_live_text(self):
        paths = [REPO / "AGENTS.md", REPO / "README.md", REPO / "docs" / "transition-plan.md"]
        paths += files_in([(folder, ("*.md", "*.py")) for folder in ("agents", "commands", "scripts", "skills", "instructions")])
        for path in paths:
            with self.subTest(path=path.relative_to(REPO).as_posix()):
                self.assertIsNone(OLD_NAME.search(path.read_text(encoding="utf-8-sig").lower()))

    def test_check_2_gives_only_the_quick_lane_the_current_branch(self):
        text = self.read("AGENTS.md")
        self.assertIn("**Quick lane (`/quick`):**", text)
        self.assertNotIn("(c) stay on", text)
        self.assertNotIn("for stay do nothing", text)

    def test_the_regular_lane_always_gets_a_new_branch(self):
        text = self.read("agents/orchestrator.md")
        self.assertNotIn("create nothing", text)
        self.assertIn("Every PR gets its own new branch", text)


class ProtectedBranchesKey(unittest.TestCase):
    """DEC-029: protecting a branch is the git host's job, so nothing live reads or teaches `protectedBranches`."""

    def test_no_live_code_or_text_names_the_key(self):
        paths = [REPO / "AGENTS.md", REPO / "README.md", REPO / "setup.py"]
        paths += files_in([
            ("execution", ("*.py",)), ("scripts", ("*.py",)), ("agents", ("*.md",)),
            ("commands", ("*.md",)), ("skills", ("*.md",)), ("instructions", ("*.md",)),
        ])
        for path in paths:
            with self.subTest(path=path.relative_to(REPO).as_posix()):
                self.assertNotIn("protectedBranches", path.read_text(encoding="utf-8-sig"))


if __name__ == "__main__":
    unittest.main()
