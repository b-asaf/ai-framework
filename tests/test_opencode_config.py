import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tools"))

from lib.opencode_config import ConfigError, catch_all_problems, load_config  # noqa: E402

CATALOG = "docs/decisions/MODEL-ASSIGNMENT-MATRIX.md"

# Rules that the real opencode.json must keep. The last matching rule wins, so each
# deny has to come after the allow it narrows (for example git branch -D after git branch *).
ALLOWED = ["git status", "git log *", "git diff *", "git branch", "git branch *",
           "git checkout -b *", "git switch -c *"]
DENIED = ["git branch -d *", "git branch -D *", "git branch --delete *", "git commit *",
          "git push*", "git merge *", "git rebase *", "git reset *",
          "gh pr ready*", "gh pr merge*", "gh pr create*", "glab mr merge*", "glab mr create*"]


class CatchAll(unittest.TestCase):
    def test_catch_all_first_passes(self):
        self.assertEqual(catch_all_problems({"bash": {"*": "ask", "git status": "allow"}}), [])

    def test_catch_all_last_is_flagged(self):
        problems = catch_all_problems({"bash": {"git status": "allow", "*": "ask"}})
        self.assertEqual(len(problems), 1)
        self.assertIn("permission.bash", problems[0])
        self.assertIn("number 2 of 2", problems[0])

    def test_blocks_without_a_catch_all_or_plain_values_are_ignored(self):
        self.assertEqual(catch_all_problems({"bash": {"git status": "allow"}, "edit": "ask"}), [])
        self.assertEqual(catch_all_problems(None), [])

    def test_every_category_is_checked(self):
        problems = catch_all_problems({"edit": {"a": "allow", "*": "ask"}, "bash": {"b": "deny", "*": "ask"}})
        self.assertEqual(len(problems), 2)

    def test_invalid_json_is_reported(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "opencode.json"
            path.write_text("{oops", encoding="utf-8")
            with self.assertRaises(ConfigError):
                load_config(path)


class RealConfig(unittest.TestCase):
    def setUp(self):
        self.bash = load_config(REPO / "opencode.json")["permission"]["bash"]
        self.order = list(self.bash)

    def test_catch_all_is_first_and_asks(self):
        self.assertEqual(self.order[0], "*")
        self.assertEqual(self.bash["*"], "ask")

    def test_autonomous_git_commands_are_allowed(self):
        for rule in ALLOWED:
            with self.subTest(rule=rule):
                self.assertEqual(self.bash.get(rule), "allow")

    def test_commit_push_merge_and_publishing_are_denied(self):
        for rule in DENIED:
            with self.subTest(rule=rule):
                self.assertEqual(self.bash.get(rule), "deny")

    def test_branch_deletion_deny_comes_after_the_branch_allow(self):
        allow_at = self.order.index("git branch *")
        for rule in ("git branch -d *", "git branch -D *", "git branch --delete *"):
            with self.subTest(rule=rule):
                self.assertGreater(self.order.index(rule), allow_at)


class ValidatorFixtures(unittest.TestCase):
    def run_validator(self, fixture):
        env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
        return subprocess.run(
            [sys.executable, str(REPO / "tools" / "validate_framework.py"),
             "tests/fixtures/" + fixture, CATALOG],
            cwd=REPO, env=env, capture_output=True,
            encoding="utf-8", errors="replace",
        )

    def test_catch_all_last_fails(self):
        result = self.run_validator("opencode-config-bad")
        output = result.stdout + result.stderr
        self.assertEqual(result.returncode, 1, output)
        self.assertIn("[opencode-config] opencode.json: permission.bash", output)

    def test_catch_all_first_passes_this_check(self):
        result = self.run_validator("opencode-config-ok")
        self.assertNotIn("[opencode-config]", result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
