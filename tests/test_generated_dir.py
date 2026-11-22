"""The folder for generated files (DEC-026, S.12b): the default, the key, and every value that is refused."""

import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from execution.runner import generated_dir  # noqa: E402

ERROR = generated_dir.GeneratedDirError
GOOD = (
    ".ai-framework", "docs/ai-framework", "a/b/c", "my-dir", "ai.framework", ".hidden/dir", "docs/ai.git",
    "my docs/ai_1",
)
BAD = (
    (None, "must be a string"), (5, "must be a string"), (True, "must be a string"),
    ([], "must be a string"), ({}, "must be a string"),
    ("", "empty"), ("   ", "empty"), (".", "empty"),
    (" a", "whitespace"), ("a ", "whitespace"), ("a\nb", "control character"), ("a\x00b", "control character"),
    ("/abs", "absolute"), ("\\abs", "absolute"), ("\\\\server\\share", "absolute"),
    ("C:/x", "absolute"), ("C:x", "absolute"),
    ("docs\\ai", "forward slashes"), ("docs\\..\\x", "forward slashes"),
    ("docs/c:x", "':'"),
    ("..", "'..'"), ("../x", "'..'"), ("a/../b", "'..'"), ("a/..", "'..'"), ("./a", "'.'"), ("a/./b", "'.'"),
    ("a//b", "empty segment"), ("a/", "empty segment"),
    (".git", "'.git'"), ("docs/.GIT/x", "'.git'"),
    ("a&b", "letters, digits"), ("a;b", "letters, digits"), ('a"b', "letters, digits"),
    ("a|b", "letters, digits"), ("a{b}", "letters, digits"), ("a$b", "letters, digits"),
    ("a%b", "letters, digits"), ("a*b", "letters, digits"), ("a<b", "letters, digits"),
)


def remove_link(link):
    for remove in (os.unlink, os.rmdir):
        try:
            remove(link)
            return
        except OSError:
            continue


class CheckValue(unittest.TestCase):
    def test_good_values_come_back_unchanged(self):
        for value in GOOD:
            with self.subTest(value=value):
                self.assertEqual(generated_dir.check_value(value), value)

    def test_bad_values_are_refused_with_a_reason(self):
        for value, fragment in BAD:
            with self.subTest(value=value):
                with self.assertRaisesRegex(ERROR, re.escape(fragment)):
                    generated_dir.check_value(value)

    def test_the_message_names_the_key_and_the_file(self):
        with self.assertRaises(ERROR) as raised:
            generated_dir.check_value("../x")
        self.assertIn("generatedDir", str(raised.exception))
        self.assertIn(".ai-framework.json", str(raised.exception))


class Target(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name).resolve()
        self.root = self.base / "repo"
        self.root.mkdir()
        self.outside = self.base / "outside"
        self.outside.mkdir()

    def set_config(self, data):
        text = data if isinstance(data, str) else json.dumps(data)
        (self.root / ".ai-framework.json").write_text(text, encoding="utf-8", newline="\n")

    def link(self, link, dest):
        """A directory link; a junction when symlinks are not allowed (Windows). Skips the test when neither works."""
        try:
            os.symlink(dest, link, target_is_directory=True)
        except (OSError, NotImplementedError):
            if os.name != "nt":
                self.skipTest("cannot create a link here")
            result = subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(dest)], capture_output=True, text=True)
            if result.returncode != 0:
                self.skipTest("cannot create a symlink or a junction here")
        self.addCleanup(remove_link, link)


class ReadTheKey(Target):
    def test_no_config_gives_the_default(self):
        self.assertEqual(generated_dir.relative_dir(self.root), ".ai-framework")
        self.assertEqual(generated_dir.absolute_dir(self.root), self.root / ".ai-framework")

    def test_a_config_without_the_key_gives_the_default(self):
        for data in ({}, {"lint": "x", "test": "y"}):
            with self.subTest(data=data):
                self.set_config(data)
                self.assertEqual(generated_dir.relative_dir(self.root), ".ai-framework")

    def test_the_key_moves_the_folder(self):
        self.set_config({"generatedDir": "docs/ai-framework"})
        self.assertEqual(generated_dir.relative_dir(self.root), "docs/ai-framework")
        self.assertEqual(generated_dir.absolute_dir(self.root), self.root / "docs" / "ai-framework")

    def test_a_config_with_a_byte_order_mark_is_read(self):
        data = json.dumps({"generatedDir": "docs/ai"}).encode("utf-8")
        (self.root / ".ai-framework.json").write_bytes(b"\xef\xbb\xbf" + data)
        self.assertEqual(generated_dir.relative_dir(self.root), "docs/ai")

    def test_every_bad_value_in_the_config_fails_closed(self):
        for value, _fragment in BAD:
            with self.subTest(value=value):
                self.set_config({"generatedDir": value})
                with self.assertRaises(ERROR):
                    generated_dir.relative_dir(self.root)

    def test_a_config_that_cannot_be_read_fails_closed(self):
        for text, message in (("{bad", "cannot be read"), ("[]", "must be a JSON object")):
            with self.subTest(text=text):
                self.set_config(text)
                with self.assertRaisesRegex(ERROR, message):
                    generated_dir.relative_dir(self.root)


class LinksThatLeaveTheRepository(Target):
    def test_a_folder_below_a_link_to_outside_is_refused(self):
        self.link(self.root / "a", self.outside)
        self.set_config({"generatedDir": "a/gen"})
        with self.assertRaisesRegex(ERROR, "inside the repository"):
            generated_dir.relative_dir(self.root)
        with self.assertRaises(ERROR):
            generated_dir.absolute_dir(self.root)

    def test_a_link_that_stays_inside_is_fine(self):
        (self.root / "real").mkdir()
        self.link(self.root / "a", self.root / "real")
        self.set_config({"generatedDir": "a/gen"})
        self.assertEqual(generated_dir.relative_dir(self.root), "a/gen")

    def test_a_link_to_the_repository_root_is_refused(self):
        self.link(self.root / "x", self.root)
        self.set_config({"generatedDir": "x"})
        with self.assertRaisesRegex(ERROR, "inside the repository"):
            generated_dir.relative_dir(self.root)

    def test_the_default_folder_as_a_link_to_outside_is_refused(self):
        self.link(self.root / ".ai-framework", self.outside)
        with self.assertRaisesRegex(ERROR, "inside the repository"):
            generated_dir.relative_dir(self.root)


if __name__ == "__main__":
    unittest.main()
