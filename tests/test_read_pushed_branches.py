import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from execution.verification.push_input import PushInputError, read_pushed_branches  # noqa: E402

A, D, ONE, TWO = "a" * 40, "d" * 40, "1" * 40, "2" * 40


def record(local_ref, local_sha, remote_ref, remote_sha):
    return f"{local_ref} {local_sha} {remote_ref} {remote_sha}\n"


class ReadPushedBranches(unittest.TestCase):
    def test_multiple_valid_branch_records(self):
        text = record("refs/heads/main", A, "refs/heads/main", D) + record(
            "refs/heads/feature/x", ONE, "refs/heads/feature/x", TWO
        )
        self.assertEqual(read_pushed_branches(text), ["main", "feature/x"])

    def test_empty_stdin(self):
        self.assertEqual(read_pushed_branches(""), [])

    def test_whitespace_only_stdin(self):
        self.assertEqual(read_pushed_branches("   \n  \n"), [])

    def test_tag_only_stdin(self):
        self.assertEqual(read_pushed_branches(record("refs/tags/v1.0", A, "refs/tags/v1.0", D)), [])

    def test_mixed_tag_and_branch_records(self):
        text = record("refs/tags/v1.0", A, "refs/tags/v1.0", D) + record("refs/heads/main", ONE, "refs/heads/main", TWO)
        self.assertEqual(read_pushed_branches(text), ["main"])

    def test_three_fields_raises(self):
        with self.assertRaises(PushInputError):
            read_pushed_branches(f"refs/heads/main {A} refs/heads/main\n")

    def test_five_fields_raises(self):
        with self.assertRaises(PushInputError):
            read_pushed_branches(f"refs/heads/main {A} refs/heads/main {D} extra\n")

    def test_malformed_record_mixed_with_valid_raises(self):
        with self.assertRaises(PushInputError):
            read_pushed_branches(record("refs/heads/main", A, "refs/heads/main", D) + "bad record here\n")

    def test_interior_blank_line_raises(self):
        text = (
            record("refs/heads/main", A, "refs/heads/main", D)
            + "\n"
            + record("refs/heads/feature/x", ONE, "refs/heads/feature/x", TWO)
        )
        with self.assertRaises(PushInputError):
            read_pushed_branches(text)

    def test_single_trailing_newline_does_not_add_phantom_entry(self):
        self.assertEqual(read_pushed_branches(record("refs/heads/main", A, "refs/heads/main", D)), ["main"])

    def test_refs_heads_with_nothing_after_raises(self):
        with self.assertRaises(PushInputError):
            read_pushed_branches(record("refs/heads/", A, "refs/heads/", D))

    def test_a_branch_deletion_still_names_the_branch(self):
        text = f"(delete) {'0' * 40} refs/heads/main {D}\n"
        self.assertEqual(read_pushed_branches(text), ["main"])


if __name__ == "__main__":
    unittest.main()
