import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPT = REPO / "scripts" / "static-analysis.py"

_spec = importlib.util.spec_from_file_location("static_analysis", SCRIPT)
sa = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sa)

HAVE_TOOLS = importlib.util.find_spec("lizard") is not None and shutil.which("jscpd") is not None
needs_tools = unittest.skipUnless(HAVE_TOOLS, "lizard and jscpd are required")

TOTAL_ROW = (
    "\u2502 Total: \u2502 4              \u2502 9           \u2502 107          \u2502 2            "
    "\u2502 2 (22.22%)       \u2502 52 (48.60%)       \u2502"
)
ZERO_ROW = (
    "\u2502 Total: \u2502 0              \u2502 0           \u2502 0            \u2502 0            "
    "\u2502 0 (0.00%)        \u2502 0 (0.00%)         \u2502"
)


def run_script(cwd, *args):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def write(root, rel, text):
    path = Path(root) / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


class ParserTest(unittest.TestCase):
    def test_lizard_warning_lines_are_extracted(self):
        text = "src/a.js:3: warning: f has 12 NLOC, 12 CCN, 50 token, 1 PARAM, 14 length\nnoise\n"
        self.assertEqual(
            sa.parse_lizard_warnings(text),
            ["src/a.js:3: warning: f has 12 NLOC, 12 CCN, 50 token, 1 PARAM, 14 length"],
        )

    def test_jscpd_total_row_is_parsed(self):
        total = sa.parse_jscpd_total("header\n" + TOTAL_ROW + "\nFound 2 clones.\n")
        self.assertEqual(total, {"files": 4, "lines": 9, "clones": 2, "percent": 22.22})

    def test_jscpd_zero_row_is_parsed(self):
        total = sa.parse_jscpd_total(ZERO_ROW)
        self.assertEqual(total["files"], 0)
        self.assertEqual(total["percent"], 0.0)

    def test_missing_summary_is_an_error(self):
        self.assertEqual(sa.classify_duplication(None, 10)[0], "ERROR")

    def test_zero_files_on_small_input_is_not_analyzed(self):
        total = {"files": 0, "lines": 0, "clones": 0, "percent": 0.0}
        self.assertEqual(sa.classify_duplication(total, 3)[0], "NOT_ANALYZED")

    def test_zero_files_on_large_input_is_an_error(self):
        total = {"files": 0, "lines": 0, "clones": 0, "percent": 0.0}
        self.assertEqual(sa.classify_duplication(total, 200)[0], "ERROR")

    def test_threshold_is_inclusive(self):
        at = {"files": 2, "lines": 100, "clones": 1, "percent": 10.0}
        over = {"files": 2, "lines": 100, "clones": 1, "percent": 10.01}
        self.assertEqual(sa.classify_duplication(at, 100)[0], "OK")
        self.assertEqual(sa.classify_duplication(over, 100)[0], "FAIL")


class ScriptTest(unittest.TestCase):
    def test_missing_path_is_an_error(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            proc = run_script(tmp, "no_such_folder")
        self.assertEqual(proc.returncode, 3)
        self.assertIn("STATUS: ERROR", proc.stdout)

    def test_unsupported_files_are_not_applicable(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            write(tmp, "notes.txt", "hello\n")
            proc = run_script(tmp, "notes.txt")
        self.assertEqual(proc.returncode, 0)
        self.assertIn("STATUS: NOT_APPLICABLE", proc.stdout)

    @needs_tools
    def test_complex_function_fails(self):
        body = "\n".join("  if (x === %d) return %d;" % (i, i) for i in range(11))
        code = "function f(x) {\n" + body + "\n  return 0;\n}\nmodule.exports = { f };\n"
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            write(tmp, "src/f.js", code)
            proc = run_script(tmp, "src")
        self.assertEqual(proc.returncode, 1, proc.stdout)
        self.assertIn("COMPLEXITY: FAIL", proc.stdout)
        self.assertIn("WARNING:", proc.stdout)

    @needs_tools
    def test_duplicated_files_fail(self):
        block = "".join('const value%d = compute(%d, "label-%d");\n' % (i, i, i) for i in range(30))
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            write(tmp, "src/a.js", block)
            write(tmp, "src/b.js", block)
            proc = run_script(tmp, "src")
        self.assertEqual(proc.returncode, 1, proc.stdout)
        self.assertIn("DUPLICATION: FAIL", proc.stdout)

    @needs_tools
    def test_tiny_file_is_partial_and_writes_nothing(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            write(tmp, "src/t.js", "const a = 1;\nmodule.exports = a;\n")
            proc = run_script(tmp, "src")
            leftovers = sorted(os.listdir(tmp))
        self.assertEqual(proc.returncode, 0, proc.stdout)
        self.assertIn("STATUS: PARTIAL", proc.stdout)
        self.assertIn("DUPLICATION: NOT_ANALYZED", proc.stdout)
        self.assertEqual(leftovers, ["src"])


if __name__ == "__main__":
    unittest.main()
