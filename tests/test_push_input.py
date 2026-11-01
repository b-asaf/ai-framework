import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from execution.verification.push_input import PushInputError, parse_push_records  # noqa: E402


class ParsePushRecords(unittest.TestCase):
    def test_empty_stdin(self):
        self.assertEqual(parse_push_records(""), [])

    def test_whitespace_only_stdin(self):
        self.assertEqual(parse_push_records("   \n  \n"), [])

    def test_single_branch_record(self):
        text = "refs/heads/main abc123 refs/heads/main def456\n"
        records = parse_push_records(text)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].local_ref, "refs/heads/main")
        self.assertEqual(records[0].local_sha, "abc123")
        self.assertEqual(records[0].remote_ref, "refs/heads/main")
        self.assertEqual(records[0].remote_sha, "def456")

    def test_multiple_records_including_tags(self):
        text = (
            "refs/heads/main abc123 refs/heads/main def456\n"
            "refs/tags/v1.0 111 refs/tags/v1.0 222\n"
        )
        records = parse_push_records(text)
        self.assertEqual(len(records), 2)
        self.assertEqual(records[1].remote_ref, "refs/tags/v1.0")

    def test_three_fields_raises(self):
        with self.assertRaises(PushInputError):
            parse_push_records("refs/heads/main abc123 refs/heads/main\n")

    def test_five_fields_raises(self):
        with self.assertRaises(PushInputError):
            parse_push_records("refs/heads/main abc123 refs/heads/main def456 extra\n")

    def test_interior_blank_line_raises(self):
        text = (
            "refs/heads/main abc123 refs/heads/main def456\n"
            "\n"
            "refs/heads/feature/x 111 refs/heads/feature/x 222\n"
        )
        with self.assertRaises(PushInputError):
            parse_push_records(text)

    def test_single_trailing_newline_does_not_add_phantom_entry(self):
        text = "refs/heads/main abc123 refs/heads/main def456\n"
        self.assertEqual(len(parse_push_records(text)), 1)


if __name__ == "__main__":
    unittest.main()
