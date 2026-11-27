import contextlib
import io
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tools"))
sys.path.insert(0, str(REPO))

import setup as framework_setup  # noqa: E402


def done(code, text=""):
    return subprocess.CompletedProcess(["x"], code, text, "")


class GraphifyVersion(unittest.TestCase):
    def test_no_command_means_no_version(self):
        with mock.patch.object(framework_setup.shutil, "which", return_value=None):
            self.assertIsNone(framework_setup._graphify_version())

    def test_the_version_line_of_the_command_is_returned(self):
        with mock.patch.object(framework_setup.shutil, "which", return_value="graphify"), \
                mock.patch.object(framework_setup.subprocess, "run", return_value=done(0, "graphify 0.9.20\n")):
            self.assertEqual(framework_setup._graphify_version(), "graphify 0.9.20")

    def test_a_command_that_fails_means_no_version(self):
        with mock.patch.object(framework_setup.shutil, "which", return_value="graphify"), \
                mock.patch.object(framework_setup.subprocess, "run", return_value=done(1, "boom")):
            self.assertIsNone(framework_setup._graphify_version())


class InstallGraphify(unittest.TestCase):
    def install(self, versions, which, result=None):
        actions = []
        out = io.StringIO()
        with mock.patch.object(framework_setup, "_graphify_version", side_effect=versions), \
                mock.patch.object(framework_setup.shutil, "which", return_value=which), \
                mock.patch.object(framework_setup.subprocess, "run", return_value=result) as run, \
                mock.patch.object(framework_setup, "ACTION_REQUIRED", actions), \
                contextlib.redirect_stdout(out):
            framework_setup.install_graphify()
        return run, actions, out.getvalue()

    def test_an_installed_graphify_is_left_alone(self):
        run, actions, text = self.install(["graphify 0.9.20"], "uv")
        run.assert_not_called()
        self.assertEqual(actions, [])
        self.assertIn("graphify 0.9.20", text)

    def test_without_uv_the_developer_gets_instructions(self):
        run, actions, _ = self.install([None], None)
        run.assert_not_called()
        self.assertEqual(len(actions), 1)

    def test_a_missing_graphify_is_installed_with_uv(self):
        run, actions, _ = self.install([None, "graphify 0.9.20"], "C:/uv.exe", done(0))
        self.assertEqual(run.call_args[0][0], ["C:/uv.exe", "tool", "install", "graphifyy"])
        self.assertEqual(actions, [])

    def test_a_failed_install_is_an_action_item(self):
        _, actions, _ = self.install([None], "C:/uv.exe", done(1))
        self.assertEqual(len(actions), 1)

    def test_an_install_that_gives_no_command_is_an_action_item(self):
        _, actions, _ = self.install([None, None], "C:/uv.exe", done(0))
        self.assertEqual(len(actions), 1)


class CheckGraphify(unittest.TestCase):
    def report(self, version):
        out = io.StringIO()
        with mock.patch.object(framework_setup, "_graphify_version", return_value=version), \
                contextlib.redirect_stdout(out):
            framework_setup.check_graphify()
        return out.getvalue()

    def test_reports_the_version(self):
        self.assertIn("graphify 0.9.20", self.report("graphify 0.9.20"))

    def test_reports_a_missing_command(self):
        self.assertIn("not found", self.report(None))


if __name__ == "__main__":
    unittest.main()
