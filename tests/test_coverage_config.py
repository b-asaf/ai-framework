"""The coverage-minimum setting: validation, and a bad value blocks the push at the gate."""
import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from execution.verification import run  # noqa: E402
from execution.verification.checks import coverage_config  # noqa: E402


def fake_run_git(argv, cwd=None, *, error):
    if argv[:2] == ["symbolic-ref", "--short"]:
        return "origin/main\n"
    raise AssertionError(f"unexpected git call: {argv}")


def setting(value):
    return {"coverage": {"minChangedLines": value}}


class ReadMinimum(unittest.TestCase):
    def test_absent_setting_gives_the_default(self):
        for config in (None, {}, {"coverage": {}}, setting(None)):
            with self.subTest(config=config):
                self.assertEqual(coverage_config.read_minimum(config), 90)

    def test_valid_values_are_returned(self):
        for value in (0, 1, 75, 100):
            with self.subTest(value=value):
                self.assertEqual(coverage_config.read_minimum(setting(value)), value)

    def test_invalid_values_raise(self):
        for value in (-1, 101, "90", 90.5, True, False, [], {}):
            with self.subTest(value=value):
                with self.assertRaises(coverage_config.CoverageConfigError):
                    coverage_config.read_minimum(setting(value))

    def test_wrong_shapes_raise(self):
        for config in ({"coverage": 5}, {"coverage": []}, [], "text"):
            with self.subTest(config=config):
                with self.assertRaises(coverage_config.CoverageConfigError):
                    coverage_config.read_minimum(config)


class GateBlocksBadSetting(unittest.TestCase):
    def run_gate(self, config_text, env=None):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as folder:
            (Path(folder) / ".ai-framework.json").write_text(config_text, encoding="utf-8", newline="\n")
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = run.main(["run.py", folder], "", env or {}, fake_run_git)
        return code, out.getvalue()

    def test_a_valid_minimum_passes(self):
        code, out = self.run_gate('{"coverage": {"minChangedLines": 0}}')
        self.assertEqual((code, out), (0, ""))

    def test_no_coverage_setting_passes(self):
        code, out = self.run_gate('{"test": "true"}')
        self.assertEqual((code, out), (0, ""))

    def test_an_invalid_minimum_blocks(self):
        code, out = self.run_gate('{"coverage": {"minChangedLines": 150}}')
        self.assertEqual(code, 1, out)
        self.assertIn("BLOCKED coverage", out)
        self.assertIn("minChangedLines", out)

    def test_a_coverage_setting_that_is_not_an_object_blocks(self):
        code, out = self.run_gate('{"coverage": 5}')
        self.assertEqual(code, 1, out)
        self.assertIn("BLOCKED coverage", out)

    def test_skip_verification_does_not_skip_the_config_check(self):
        code, out = self.run_gate('{"coverage": {"minChangedLines": "high"}}', {"SKIP_VERIFICATION": "1"})
        self.assertEqual(code, 1, out)
        self.assertIn("BLOCKED coverage", out)


if __name__ == "__main__":
    unittest.main()
