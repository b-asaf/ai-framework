import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from execution.runner import benchmark, tree  # noqa: E402


def write(root, relative, text):
    path = Path(root) / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


class ChangedFiles(unittest.TestCase):
    def test_added_modified_and_deleted_are_told_apart_and_sorted(self):
        result = tree.changed_files({"a": "1", "b": "1", "c": "1"}, {"a": "1", "b": "2", "e": "1", "d": "1"})
        self.assertEqual(result.added, ("d", "e"))
        self.assertEqual(result.modified, ("b",))
        self.assertEqual(result.deleted, ("c",))
        self.assertEqual(result.everything, ("b", "c", "d", "e"))

    def test_identical_snapshots_change_nothing(self):
        self.assertEqual(tree.changed_files({"a": "1"}, {"a": "1"}), tree.Changes())


class Shared(unittest.TestCase):
    def test_the_benchmark_uses_this_snapshot(self):
        self.assertIs(benchmark.snapshot, tree.snapshot)

    def test_a_real_folder_shows_its_changes_and_ignores_git(self):
        with tempfile.TemporaryDirectory() as tmp:
            for name in ("src/a.ts", "keep.txt", ".git/HEAD"):
                write(tmp, name, "one")
            before = tree.snapshot(tmp)
            write(tmp, "src/a.ts", "two")
            write(tmp, "src/a.test.ts", "new")
            write(tmp, ".git/index", "ignored")
            (Path(tmp) / "keep.txt").unlink()
            result = tree.changed_files(before, tree.snapshot(tmp))
        self.assertEqual((result.added, result.modified, result.deleted), (("src/a.test.ts",), ("src/a.ts",), ("keep.txt",)))


if __name__ == "__main__":
    unittest.main()
