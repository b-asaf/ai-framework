import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from execution.runner import facts, qa_cases  # noqa: E402

PERCENT_TEST = """import { test } from "node:test";
import assert from "node:assert/strict";
import { percent } from "./percent.ts";

test("a zero total gives zero", () => {
  assert.equal(percent(5, 0), 0);
});

test("the result is rounded", () => {
  assert.equal(percent(2, 3), 67);
});
"""
TITLE_TEST = """import { test } from "node:test";
import assert from "node:assert/strict";
import { titleCase } from "./title.ts";

test("small words stay lower case except the first word", () => {
  assert.equal(titleCase("the lord of the rings"), "The Lord of the Rings");
});
"""
REFERENCE = {
    "percent-zero-total": ("src/percent.test.ts", PERCENT_TEST),
    "title-case-private-helper": ("src/title.test.ts", TITLE_TEST),
}
NODE = shutil.which("node")


def node_is_new_enough():
    if not NODE:
        return False
    try:
        out = subprocess.run([NODE, "--version"], capture_output=True, text=True, timeout=30).stdout
        return int(out.strip().lstrip("v").split(".")[0]) >= 24
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return False


class Cases(unittest.TestCase):
    def test_ids_are_unique_and_one_case_tempts_an_edit(self):
        self.assertEqual(len(set(qa_cases.CASE_IDS)), len(qa_cases.CASES))
        self.assertTrue(any(case.tempts_edit for case in qa_cases.CASES))

    def test_the_mutant_differs_from_the_source_in_a_production_file(self):
        for case in qa_cases.CASES:
            with self.subTest(case=case.id):
                self.assertNotEqual(case.mutant, case.source)
                self.assertFalse(qa_cases.is_test_file(case.path))

    def test_an_unknown_case_names_the_known_ones(self):
        with self.assertRaisesRegex(ValueError, "percent-zero-total"):
            qa_cases.get_case("nope")

    def test_the_test_pattern(self):
        for path in ("src/a.test.ts", "a.test.ts", "src\\a.test.ts"):
            self.assertTrue(qa_cases.is_test_file(path), path)
        for path in ("src/a.ts", "src/test.ts", "src/a.test.ts.bak", ".ai-framework.json"):
            self.assertFalse(qa_cases.is_test_file(path), path)

    def test_the_patch_adds_the_production_file(self):
        for case in qa_cases.CASES:
            with self.subTest(case=case.id):
                patch = qa_cases.make_patch(case)
                self.assertIn(f"diff --git a/{case.path} b/{case.path}", patch)
                self.assertIn("+" + case.source.splitlines()[0], patch.splitlines())

    def test_the_patch_file_holds_the_patch(self):
        case = qa_cases.CASES[0]
        with tempfile.TemporaryDirectory() as tmp:
            path = qa_cases.write_patch(case, Path(tmp) / "case.patch")
            self.assertEqual(path.read_text(encoding="utf-8"), qa_cases.make_patch(case))


class Projects(unittest.TestCase):
    def test_the_project_declares_the_pattern_and_the_test_command(self):
        for case in qa_cases.CASES:
            with self.subTest(case=case.id), tempfile.TemporaryDirectory() as tmp:
                root = qa_cases.build_project(case, Path(tmp) / "p")
                patterns = (root / "docs/project-overview/sub/patterns.md").read_text(encoding="utf-8")
                self.assertIn(".test.ts", patterns)
                self.assertEqual(facts.test_command(root), "node --test")
                self.assertTrue((root / "docs/project-overview/stack.md").is_file())
                self.assertTrue((root / "docs/project-overview/sub/stack.md").is_file())
                self.assertEqual((root / case.path).read_text(encoding="utf-8"), case.source)

    def test_the_mutant_project_has_the_defect_and_the_extra_files(self):
        case = qa_cases.CASES[0]
        with tempfile.TemporaryDirectory() as tmp:
            root = qa_cases.build_project(case, Path(tmp) / "m", mutant=True, extra={"src/x.test.ts": "t\n"})
            self.assertEqual((root / case.path).read_text(encoding="utf-8"), case.mutant)
            self.assertEqual((root / "src/x.test.ts").read_text(encoding="utf-8"), "t\n")


@unittest.skipUnless(node_is_new_enough(), "node 24 or newer is needed to run .ts tests")
class FixturesBehave(unittest.TestCase):
    def run_tests(self, root):
        done = subprocess.run(
            [NODE, "--test"], cwd=str(root), stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=120
        )
        return done.returncode

    def test_reference_tests_pass_on_the_source_and_fail_on_the_mutant(self):
        for case in qa_cases.CASES:
            name, text = REFERENCE[case.id]
            with self.subTest(case=case.id), tempfile.TemporaryDirectory() as tmp:
                good = qa_cases.build_project(case, Path(tmp) / "good", extra={name: text})
                bad = qa_cases.build_project(case, Path(tmp) / "bad", mutant=True, extra={name: text})
                self.assertEqual(self.run_tests(good), 0)
                self.assertNotEqual(self.run_tests(bad), 0)


if __name__ == "__main__":
    unittest.main()
