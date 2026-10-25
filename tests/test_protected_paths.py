import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from execution.verification.checks.protected_paths import (  # noqa: E402
    ProtectedPathError,
    find_violations,
    snapshot,
)

PROTECTED = ["hooks", "AGENTS.md"]


def write(root, relative, content):
    path = Path(root) / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


class Snapshot(unittest.TestCase):
    def test_hashes_files_under_protected_paths_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            write(tmp, "hooks/pre-push", "a")
            write(tmp, "AGENTS.md", "b")
            write(tmp, "other.txt", "c")
            result = snapshot(tmp, PROTECTED)
        self.assertEqual(set(result), {"hooks/pre-push", "AGENTS.md"})

    def test_missing_protected_path_is_absent_not_an_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = snapshot(tmp, PROTECTED)
        self.assertEqual(result, {})

    def test_unreadable_file_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            write(tmp, "AGENTS.md", "b")
            with mock.patch.object(Path, "read_bytes", side_effect=OSError("denied")):
                with self.assertRaises(ProtectedPathError):
                    snapshot(tmp, PROTECTED)

    def test_dotdot_protected_path_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ProtectedPathError):
                snapshot(tmp, ["../sibling"])

    def test_absolute_protected_path_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            absolute = str(Path(tmp) / "hooks")
            with self.assertRaises(ProtectedPathError):
                snapshot(tmp, [absolute])

    def test_recursive_nested_files_are_picked_up(self):
        with tempfile.TemporaryDirectory() as tmp:
            write(tmp, "hooks/sub/deep/file.txt", "a")
            result = snapshot(tmp, PROTECTED)
        self.assertIn("hooks/sub/deep/file.txt", result)

    def test_content_change_produces_different_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            protected_file = write(tmp, "AGENTS.md", "a")
            before = snapshot(tmp, PROTECTED)
            protected_file.write_text("b", encoding="utf-8")
            after = snapshot(tmp, PROTECTED)
        self.assertNotEqual(before["AGENTS.md"], after["AGENTS.md"])

    def test_unreadable_symlink_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            external_dir = Path(tmp).parent / "protected_paths_readlink_test"
            external_dir.mkdir(exist_ok=True)
            try:
                external_file = external_dir / "external.txt"
                external_file.write_text("a", encoding="utf-8")

                protected_file = Path(tmp) / "AGENTS.md"
                try:
                    protected_file.symlink_to(external_file)
                except (OSError, NotImplementedError) as error:
                    self.skipTest(f"symlink creation unavailable: {error}")

                with mock.patch.object(Path, "readlink", side_effect=OSError("denied")):
                    with self.assertRaises(ProtectedPathError):
                        snapshot(tmp, PROTECTED)
            finally:
                for entry in external_dir.iterdir():
                    entry.unlink()
                external_dir.rmdir()

    def test_sibling_prefix_path_is_not_protected(self):
        with tempfile.TemporaryDirectory() as tmp:
            write(tmp, "hooks-other/file.txt", "a")
            result = snapshot(tmp, ["hooks"])
            self.assertNotIn("hooks-other/file.txt", result)

        before = {"hooks-other/file.txt": "x"}
        after = {"hooks-other/file.txt": "y"}
        self.assertEqual(find_violations(before, after, ["hooks"]), [])

    def test_symlink_swap_changes_snapshot_entry(self):
        with tempfile.TemporaryDirectory() as tmp:
            external_dir = Path(tmp).parent / "protected_paths_external_test"
            external_dir.mkdir(exist_ok=True)
            try:
                external_file = external_dir / "external.txt"
                external_file.write_text("a", encoding="utf-8")

                protected_file = write(tmp, "AGENTS.md", "a")
                before = snapshot(tmp, PROTECTED)

                protected_file.unlink()
                try:
                    protected_file.symlink_to(external_file)
                except (OSError, NotImplementedError) as error:
                    self.skipTest(f"symlink creation unavailable: {error}")

                after = snapshot(tmp, PROTECTED)
                self.assertNotEqual(before["AGENTS.md"], after["AGENTS.md"])
                violations = find_violations(before, after, PROTECTED)
                self.assertEqual(len(violations), 1)
                self.assertEqual(violations[0]["reason"], "modified")
            finally:
                for entry in external_dir.iterdir():
                    entry.unlink()
                external_dir.rmdir()


class FindViolations(unittest.TestCase):
    def test_no_changes_is_clean(self):
        before = {"hooks/pre-push": "x"}
        after = {"hooks/pre-push": "x"}
        self.assertEqual(find_violations(before, after, PROTECTED), [])

    def test_modified_protected_file_is_reported(self):
        before = {"hooks/pre-push": "x"}
        after = {"hooks/pre-push": "y"}
        violations = find_violations(before, after, PROTECTED)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["reason"], "modified")
        self.assertEqual(violations[0]["path"], "hooks/pre-push")
        self.assertEqual(violations[0]["protected_path"], "hooks")

    def test_added_and_removed_protected_files_are_reported(self):
        before = {"hooks/pre-push": "x"}
        after = {"hooks/pre-push": "x", "AGENTS.md": "new"}
        violations = find_violations(before, after, PROTECTED)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["reason"], "added")

        before = {"hooks/pre-push": "x"}
        after = {}
        violations = find_violations(before, after, PROTECTED)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["reason"], "removed")

    def test_non_protected_file_changes_are_ignored(self):
        before = {"other.txt": "x"}
        after = {"other.txt": "y"}
        self.assertEqual(find_violations(before, after, PROTECTED), [])


if __name__ == "__main__":
    unittest.main()
