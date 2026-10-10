import os
import subprocess
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tools"))

from lib.frontmatter import lint_frontmatter  # noqa: E402

CATALOG = "docs/decisions/MODEL-ASSIGNMENT-MATRIX.md"

BAD = r'''permission:
  external_directory:
    "D:\ai-framework\skills\*": allow'''
SINGLE = r"""permission:
  external_directory:
    'D:\ai-framework\skills\*': allow"""
DOUBLED = r'''permission:
  external_directory:
    "D:\\ai-framework\\skills\\*": allow'''
ESCAPED_QUOTE = r'''description: "say \"hi\""'''
POWERSHELL = r'''permission:
  bash:
    'powershell -File "$env:USERPROFILE\.config\opencode\scripts\git-context.ps1"': allow'''
COMMENT = r'''description: ok # "C:\temp"'''
PLAIN = r'''path: C:\temp\x'''
APOSTROPHE = r'''description: it's fine "C:\temp"'''


def wrap(body):
    return "---\n" + body + "\n---\nBody\n"


class LintFrontmatter(unittest.TestCase):
    def test_flags_unsafe_escapes_with_the_file_line(self):
        issues = lint_frontmatter(wrap(BAD))
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0][0], 4)
        for sequence in (r"\a", r"\s", r"\*"):
            self.assertIn(sequence, issues[0][1])

    def test_single_quotes_are_fine(self):
        self.assertEqual(lint_frontmatter(wrap(SINGLE)), [])

    def test_doubled_backslashes_are_fine(self):
        self.assertEqual(lint_frontmatter(wrap(DOUBLED)), [])

    def test_escaped_quote_is_fine(self):
        self.assertEqual(lint_frontmatter(wrap(ESCAPED_QUOTE)), [])

    def test_double_quotes_inside_single_quotes_are_ignored(self):
        self.assertEqual(lint_frontmatter(wrap(POWERSHELL)), [])

    def test_comments_and_plain_values_are_ignored(self):
        self.assertEqual(lint_frontmatter(wrap(COMMENT)), [])
        self.assertEqual(lint_frontmatter(wrap(PLAIN)), [])

    def test_apostrophe_in_a_plain_value_does_not_open_a_string(self):
        self.assertEqual(lint_frontmatter(wrap(APOSTROPHE)), [])

    def test_text_outside_the_frontmatter_is_ignored(self):
        text = "---\nmode: subagent\n---\nBody with " + r'"C:\temp"' + "\n"
        self.assertEqual(lint_frontmatter(text), [])


class ValidatorFixtures(unittest.TestCase):
    def run_validator(self, fixture):
        env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
        return subprocess.run(
            [sys.executable, str(REPO / "tools" / "validate_framework.py"),
             "tests/fixtures/" + fixture, CATALOG],
            cwd=REPO, env=env, capture_output=True,
            encoding="utf-8", errors="replace",
        )

    def test_bad_fixture_is_flagged(self):
        result = self.run_validator("bad-escape")
        output = result.stdout + result.stderr
        self.assertEqual(result.returncode, 1, output)
        self.assertIn("unsafe escape", output)
        self.assertIn("bad.md:7", output)

    def test_good_fixture_has_no_frontmatter_issue(self):
        result = self.run_validator("good-escape")
        output = result.stdout + result.stderr
        self.assertNotIn("unsafe escape", output)


if __name__ == "__main__":
    unittest.main()
