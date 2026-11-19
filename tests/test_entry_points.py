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


class EntryPoint(unittest.TestCase):
    def test_the_validator_passes_on_the_real_repo(self):
        result = run("validate_framework.py")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("All agent validation checks passed", result.stdout)

    def test_the_validator_fails_on_a_failing_fixture(self):
        result = run("validate_framework.py", "tests/fixtures/dec014-same-model", CATALOG)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
