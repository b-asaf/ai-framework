import os
import subprocess
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
CATALOG = "docs/decisions/MODEL-ASSIGNMENT-MATRIX.md"


def run(script, *args):
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    return subprocess.run(
        [sys.executable, str(REPO / "tools" / script), *args],
        cwd=REPO, env=env, capture_output=True,
        encoding="utf-8", errors="replace",
    )


class EntryPoints(unittest.TestCase):
    def test_both_entry_points_pass_on_the_real_repo(self):
        for script in ("validate_framework.py", "validate_agents.py"):
            with self.subTest(script=script):
                result = run(script)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn("All agent validation checks passed", result.stdout)

    def test_wrapper_gives_the_same_result_on_a_failing_fixture(self):
        args = ("tests/fixtures/dec014-same-model", CATALOG)
        framework = run("validate_framework.py", *args)
        wrapper = run("validate_agents.py", *args)
        self.assertEqual(framework.returncode, 1, framework.stdout + framework.stderr)
        self.assertEqual(wrapper.returncode, framework.returncode)
        self.assertEqual(wrapper.stdout, framework.stdout)


if __name__ == "__main__":
    unittest.main()
