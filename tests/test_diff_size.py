"""The diff-size check (F68, DEC-020): counting, the limit, the base, and the absence of any skip."""

import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from execution.verification.checks import diff_size  # noqa: E402

HEAD = "diff --git a/x.js b/x.js\nindex 1..2 100644\n--- a/x.js\n+++ b/x.js\n@@ -1,0 +1,2 @@\n"
SHA = "a" * 40


def fake_git(answers):
    def run_git(argv):
        if argv[0] not in answers:
            raise diff_size.DiffSizeError(f"git {argv} failed")
        return answers[argv[0]]

    return run_git


class ReadMaxLines(unittest.TestCase):
    def test_absent_gives_the_default(self):
        for config in (None, {}):
            self.assertEqual(diff_size.read_max_lines(config), 400)

    def test_valid_values_are_returned(self):
        for value in (1, 400, 1000):
            with self.subTest(value=value):
                self.assertEqual(diff_size.read_max_lines({"maxDiffLines": value}), value)

    def test_invalid_values_raise(self):
        for value in (None, 0, -1, "400", 4.5, True, []):
            with self.subTest(value=value):
                with self.assertRaises(diff_size.DiffSizeError):
                    diff_size.read_max_lines({"maxDiffLines": value})

    def test_a_config_that_is_not_an_object_raises(self):
        with self.assertRaises(diff_size.DiffSizeError):
            diff_size.read_max_lines([])


class CountMeaningfulLines(unittest.TestCase):
    def count(self, body):
        return diff_size.count_meaningful_lines(HEAD + body)

    def test_added_and_removed_lines_count(self):
        self.assertEqual(self.count("+a\n-b\n+c\n"), 3)

    def test_the_file_header_is_not_counted(self):
        self.assertEqual(diff_size.count_meaningful_lines(HEAD), 0)

    def test_lines_that_start_with_a_plus_or_minus_count(self):
        self.assertEqual(self.count("+- a bullet\n-- old rule\n++x\n"), 3)

    def test_blank_and_import_only_lines_do_not_count(self):
        body = "+\n+   \n+import a from 'a'\n+export { b } from './b'\n+const c = require('c')\n+real = 1\n"
        self.assertEqual(self.count(body), 1)

    def test_each_file_starts_a_new_header(self):
        second = "diff --git a/y b/y\n--- a/y\n+++ b/y\n@@ -1 +1 @@\n-b\n+c\n"
        self.assertEqual(self.count("+a\n" + second), 3)

    def test_the_no_newline_marker_is_not_counted(self):
        self.assertEqual(self.count("+a\n\\ No newline at end of file\n"), 1)


class FindViolations(unittest.TestCase):
    def test_a_branch_over_the_limit_is_a_violation(self):
        found = diff_size.find_violations([("feature/x", 401, "origin/main")], 400)
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["check"], "diff_size")
        self.assertIn("401 meaningful lines against origin/main", found[0]["reason"])
        self.assertIn("atomic-changes limit of 400", found[0]["reason"])

    def test_a_branch_at_the_limit_passes(self):
        measurements = [("a", 400, "origin/main"), ("b", 0, "origin/main")]
        self.assertEqual(diff_size.find_violations(measurements, 400), [])


class ReadBase(unittest.TestCase):
    def test_a_configured_base_wins_when_it_resolves(self):
        base = diff_size.read_base({"diffBaseBranch": " origin/dev "}, run_git=fake_git({"rev-parse": "abc\n"}))
        self.assertEqual(base, "origin/dev")

    def test_a_configured_base_that_does_not_resolve_raises(self):
        with self.assertRaisesRegex(diff_size.DiffSizeError, "does not resolve"):
            diff_size.read_base({"diffBaseBranch": "nope"}, run_git=fake_git({}))

    def test_bad_configured_values_raise(self):
        for value in (None, "", "  ", 5, "-x"):
            with self.subTest(value=value):
                with self.assertRaises(diff_size.DiffSizeError):
                    diff_size.read_base({"diffBaseBranch": value}, run_git=fake_git({"rev-parse": "x"}))

    def test_origin_head_is_the_default_base(self):
        base = diff_size.read_base({}, run_git=fake_git({"symbolic-ref": "origin/main\n"}))
        self.assertEqual(base, "origin/main")

    def test_no_base_raises_with_a_fix_message(self):
        for answers in ({}, {"symbolic-ref": "main\n"}, {"symbolic-ref": "origin/\n"}):
            with self.subTest(answers=answers):
                with self.assertRaisesRegex(diff_size.DiffSizeError, "origin/HEAD is not set"):
                    diff_size.read_base({}, run_git=fake_git(answers))


class Measure(unittest.TestCase):
    def test_a_deleted_branch_has_no_lines_and_needs_no_git(self):
        self.assertEqual(diff_size.measure("0" * 40, "origin/main", run_git=fake_git({})), 0)

    def test_the_diff_from_the_merge_base_is_counted(self):
        git = fake_git({"merge-base": "abc123\n", "diff": HEAD + "+a\n+b\n"})
        self.assertEqual(diff_size.measure(SHA, "origin/main", run_git=git), 2)

    def test_an_unreadable_merge_base_raises(self):
        git = fake_git({"merge-base": "a b\n", "diff": ""})
        with self.assertRaisesRegex(diff_size.DiffSizeError, "merge-base"):
            diff_size.measure(SHA, "origin/main", run_git=git)


if __name__ == "__main__":
    unittest.main()
