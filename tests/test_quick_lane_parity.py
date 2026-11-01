import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from execution.verification.checks import quick_lane  # noqa: E402

SCRIPT = REPO / "scripts" / "quick-lane-check.py"


def _load_script_module():
    spec = importlib.util.spec_from_file_location("quick_lane_check_script", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class QuickLaneParity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.script = _load_script_module()

    def test_restricted_patterns_agree(self):
        import fnmatch

        names = (
            "package.json", "package-lock.json", "yarn.lock", "pnpm-lock.yaml",
            "pom.xml", "build.gradle", "build.gradle.kts", "requirements.txt",
            "requirements-dev.txt", "pyproject.toml", "poetry.lock", "Pipfile",
            "Pipfile.lock", ".ai-framework.json",
        )
        for name in names:
            with self.subTest(name=name):
                script_match = any(fnmatch.fnmatch(name, p) for p in self.script.RESTRICTED_PATTERNS)
                check_match = any(fnmatch.fnmatchcase(name, p) for p in quick_lane.RESTRICTED_PATTERNS)
                self.assertTrue(script_match, f"{name} not matched by the script's patterns")
                self.assertTrue(check_match, f"{name} not matched by the check's patterns")

    def test_default_limits_agree(self):
        self.assertEqual(self.script.DEFAULT_MAX_FILES, quick_lane.DEFAULT_MAX_FILES)
        self.assertEqual(self.script.DEFAULT_MAX_LINES, quick_lane.DEFAULT_MAX_LINES)

    def test_valid_override_agrees(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = {"quickLane": {"maxFiles": 1, "maxLines": 5}}
            (Path(tmp) / ".ai-framework.json").write_text(json.dumps(config), encoding="utf-8")
            script_result = self.script.read_limits(Path(tmp), None, None)
            self.assertEqual(script_result, quick_lane.read_limits(config))

    def test_no_config_defaults_agree(self):
        with tempfile.TemporaryDirectory() as tmp:
            script_result = self.script.read_limits(Path(tmp), None, None)
            self.assertEqual(script_result, quick_lane.read_limits(None))

    def test_non_positive_int_fails_closed_in_both(self):
        with self.assertRaises(quick_lane.QuickLaneError):
            quick_lane.read_limits({"quickLane": {"maxFiles": 0}})
        with tempfile.TemporaryDirectory() as tmp:
            config = {"quickLane": {"maxFiles": 0}}
            (Path(tmp) / ".ai-framework.json").write_text(json.dumps(config), encoding="utf-8")
            with self.assertRaises(self.script.CheckError):
                self.script.read_limits(Path(tmp), None, None)


if __name__ == "__main__":
    unittest.main()

