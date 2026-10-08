import os
import subprocess
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


class ValidatorOnRealRepo(unittest.TestCase):
    def test_validator_passes(self):
        env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
        result = subprocess.run(
            [sys.executable, str(REPO / "tools" / "validate_agents.py")],
            cwd=REPO, env=env, capture_output=True,
            encoding="utf-8", errors="replace",
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("All agent validation checks passed", result.stdout)


if __name__ == "__main__":
    unittest.main()
