import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from execution.runner import bench_cases, preflight  # noqa: E402

GENERIC_REMARK = "Consider a clearer name and add a unit test for this function."
BUG_CASES = [case for case in bench_cases.CASES if case.kind == "bug"]
CLEAN_CASES = [case for case in bench_cases.CASES if case.kind == "clean"]


class CaseSet(unittest.TestCase):
    def test_ids_are_unique_and_there_are_enough_cases(self):
        ids = [case.id for case in bench_cases.CASES]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(bench_cases.CASE_IDS, tuple(ids))
        self.assertGreaterEqual(len(BUG_CASES), 4)
        self.assertGreaterEqual(len(CLEAN_CASES), 2)

    def test_a_case_has_a_bug_exactly_when_it_is_a_bug_case(self):
        for case in bench_cases.CASES:
            with self.subTest(case=case.id):
                self.assertIn(case.kind, ("bug", "clean"))
                self.assertEqual(case.bug is not None, case.kind == "bug")

    def test_get_case(self):
        self.assertEqual(bench_cases.get_case("off-by-one-loop").id, "off-by-one-loop")
        with self.assertRaisesRegex(ValueError, "unknown case"):
            bench_cases.get_case("nope")

    def test_every_change_really_changes_a_file_and_ends_with_a_newline(self):
        for case in bench_cases.CASES:
            for path, (before, after) in case.changes.items():
                with self.subTest(case=case.id, path=path):
                    self.assertNotEqual(before, after)
                    self.assertTrue(after.endswith("\n"))


class Diffs(unittest.TestCase):
    def test_every_diff_has_a_git_header_and_names_every_changed_file(self):
        for case in bench_cases.CASES:
            with self.subTest(case=case.id):
                diff = bench_cases.make_diff(case.changes)
                self.assertTrue(diff.startswith("diff --git a/"))
                for path in case.changes:
                    self.assertIn(f"+++ b/{path}", diff)

    def test_a_new_file_is_diffed_against_dev_null(self):
        diff = bench_cases.make_diff({"a.txt": (None, "one\n")})
        self.assertIn("new file mode", diff)
        self.assertIn("--- /dev/null", diff)
        self.assertIn("+one", diff)

    def test_the_bug_marker_is_one_added_line_and_the_lines_are_computed(self):
        for case in BUG_CASES:
            with self.subTest(case=case.id):
                diff = bench_cases.make_diff(case.changes)
                added = [line for line in diff.splitlines() if line.startswith("+") and not line.startswith("+++")]
                self.assertEqual(len([line for line in added if case.bug.marker in line]), 1)
                self.assertIn(case.bug.file, case.changes)
                file_line, patch_line = bench_cases.bug_lines(case)
                self.assertIn(case.bug.marker, case.changes[case.bug.file][1].splitlines()[file_line - 1])
                self.assertIn(case.bug.marker, diff.splitlines()[patch_line - 1])

    def test_the_first_case_has_its_bug_on_line_3_of_the_file_and_line_8_of_the_patch(self):
        self.assertEqual(bench_cases.bug_lines(bench_cases.get_case("off-by-one-loop")), (3, 8))

    def test_each_pattern_matches_its_example_and_not_a_generic_remark(self):
        for case in BUG_CASES:
            with self.subTest(case=case.id):
                self.assertIsNotNone(re.search(case.bug.pattern, case.bug.example, re.I))
                self.assertIsNone(re.search(case.bug.pattern, GENERIC_REMARK, re.I))


class Targets(unittest.TestCase):
    def test_build_target_writes_the_project_after_the_change_and_the_gate_files(self):
        case = bench_cases.get_case("null-from-repository")
        with tempfile.TemporaryDirectory() as tmp:
            root = bench_cases.build_target(case, Path(tmp) / "t")
            for path, text in case.context.items():
                self.assertEqual((root / path).read_text(encoding="utf-8"), text)
            for path, (_, after) in case.changes.items():
                self.assertEqual((root / path).read_text(encoding="utf-8"), after)
            stack = (root / "docs" / "project-overview" / "stack.md").read_text(encoding="utf-8")
            self.assertNotIn("[XXX]", stack)
            self.assertIn("Language", stack)
            self.assertEqual(json.loads((root / ".ai-framework.json").read_text(encoding="utf-8")), {})

    def test_every_target_passes_the_runner_preflight(self):
        for case in bench_cases.CASES:
            with self.subTest(case=case.id):
                with tempfile.TemporaryDirectory() as tmp:
                    root = bench_cases.build_target(case, Path(tmp) / "t")
                    self.assertEqual(preflight.check_target(root, bench_cases.ROLE, {}), [])

    def test_write_diff_writes_the_diff_with_line_feeds_only(self):
        case = bench_cases.get_case("clean-guard-with-test")
        with tempfile.TemporaryDirectory() as tmp:
            path = bench_cases.write_diff(case, Path(tmp) / "case.patch")
            data = path.read_bytes()
        self.assertEqual(data.decode("utf-8"), bench_cases.make_diff(case.changes))
        self.assertNotIn(b"\r", data)


if __name__ == "__main__":
    unittest.main()
