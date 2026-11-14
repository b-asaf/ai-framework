import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from execution.runner import tree  # noqa: E402


def make(tmp, files):
    for name, data in files.items():
        path = Path(tmp) / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)


class ReadFiles(unittest.TestCase):
    def test_the_text_of_each_named_file_is_returned_with_its_line_endings(self):
        with tempfile.TemporaryDirectory() as tmp:
            make(tmp, {"src/a.test.ts": b"one\n", "b.txt": b"two\r\n"})
            result = tree.read_files(tmp, ["src/a.test.ts", "b.txt"])
        self.assertEqual(result, {"src/a.test.ts": "one\n", "b.txt": "two\r\n"})

    def test_no_names_give_an_empty_result(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(tree.read_files(tmp, []), {})

    def test_a_file_over_the_file_limit_is_none_and_the_next_one_is_still_read(self):
        with tempfile.TemporaryDirectory() as tmp:
            make(tmp, {"big.txt": b"123456", "ok.txt": b"12345"})
            result = tree.read_files(tmp, ["big.txt", "ok.txt"], max_file=5)
        self.assertEqual(result, {"big.txt": None, "ok.txt": "12345"})

    def test_a_file_that_is_not_utf8_is_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            make(tmp, {"bin.dat": b"\xff\xfe\x00"})
            self.assertEqual(tree.read_files(tmp, ["bin.dat"]), {"bin.dat": None})

    def test_a_missing_file_is_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(tree.read_files(tmp, ["gone.txt"]), {"gone.txt": None})

    def test_the_total_budget_counts_only_what_was_read(self):
        with tempfile.TemporaryDirectory() as tmp:
            make(tmp, {"a": b"aaaaaa", "b": b"bbbbbb", "c": b"cccc"})
            result = tree.read_files(tmp, ["a", "b", "c"], max_file=10, max_total=10)
        self.assertEqual(result, {"a": "aaaaaa", "b": None, "c": "cccc"})

    def test_a_normal_test_file_is_inside_the_default_limits(self):
        with tempfile.TemporaryDirectory() as tmp:
            text = "test('x', () => {});\n" * 150
            make(tmp, {"x.test.ts": text.encode("utf-8")})
            self.assertEqual(tree.read_files(tmp, ["x.test.ts"]), {"x.test.ts": text})


if __name__ == "__main__":
    unittest.main()
