"""Hardening of the pre-push gate found in the review of PR 78: object ids, an unreadable config, the first
concrete protected branch, a gate that crashes, and a branch name the console code page cannot encode."""

import contextlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from execution.verification import push_input, run  # noqa: E402

SHA1 = "a" * 40
SHA256 = "b" * 64
ZERO = "0" * 40
SCRIPT = REPO / "execution" / "verification" / "run.py"


def push_line(local, remote):
    return f"refs/heads/x {local} refs/heads/x {remote}\n"


class ObjectIds(unittest.TestCase):
    def test_full_length_hex_ids_are_accepted(self):
        for local, remote in ((SHA1, ZERO), (SHA256, "0" * 64), ("AbCdEf0123456789" * 2 + "01234567", SHA1)):
            with self.subTest(local=local):
                records = push_input.parse_push_records(push_line(local, remote))
                self.assertEqual((records[0].local_sha, records[0].remote_sha), (local, remote))

    def test_anything_that_is_not_a_full_hex_id_is_refused(self):
        for bad in ("abc123", "a" * 39, "a" * 41, "g" * 40, "-" + "a" * 39, "--output=x", "HEAD"):
            for position in (0, 1):
                ids = [SHA1, SHA1]
                ids[position] = bad
                with self.subTest(bad=bad, position=position):
                    with self.assertRaisesRegex(push_input.PushInputError, "object id"):
                        push_input.parse_push_records(push_line(*ids))

    def test_a_delete_record_is_accepted(self):
        records = push_input.parse_push_records(f"(delete) {ZERO} refs/heads/x {SHA1}\n")
        self.assertEqual(records[0].local_ref, "(delete)")


class UnreadableConfig(unittest.TestCase):
    def test_a_config_that_cannot_be_read_is_a_violation_not_a_traceback(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            (Path(tmp) / ".ai-framework.json").write_text("{}", encoding="utf-8")
            with mock.patch.object(Path, "read_text", side_effect=PermissionError("denied")):
                config, violation = run._read_config(tmp)
        self.assertEqual(config, {})
        self.assertEqual(violation["check"], "config")
        self.assertIn("cannot be read", violation["reason"])


class FirstConcrete(unittest.TestCase):
    def test_the_first_plain_name_is_the_base_for_a_new_branch(self):
        self.assertEqual(run._first_concrete(["release/*", "main", "dev"]), "main")
        self.assertEqual(run._first_concrete(["main"]), "main")

    def test_patterns_are_not_a_base_and_nothing_gives_none(self):
        for names in ([], ["release/*"], ["a?b", "c[de]"]):
            with self.subTest(names=names):
                self.assertIsNone(run._first_concrete(names))


class GateCrash(unittest.TestCase):
    def test_an_unexpected_error_is_a_readable_block(self):
        out = io.StringIO()
        with mock.patch.object(run, "main", side_effect=RuntimeError("boom")), contextlib.redirect_stdout(out):
            code = run.main_or_block(["run.py"], "", {}, None)
        self.assertEqual(code, 1)
        self.assertIn("BLOCKED gate: internal error: RuntimeError: boom", out.getvalue())
        self.assertIn("--no-verify", out.getvalue())

    def test_a_normal_result_passes_through(self):
        with mock.patch.object(run, "main", return_value=0):
            self.assertEqual(run.main_or_block(["run.py"], "", {}, None), 0)


class NonAsciiBranch(unittest.TestCase):
    def test_a_branch_name_the_console_code_page_cannot_encode_is_reported_not_a_traceback(self):
        branch = "\u0436"
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            subprocess.run(["git", "init", "-q", "--template=", tmp], check=True, capture_output=True)
            config = json.dumps({"protectedBranches": [branch]}, ensure_ascii=False)
            (Path(tmp) / ".ai-framework.json").write_bytes(config.encode("utf-8"))
            line = f"refs/heads/{branch} {ZERO} refs/heads/{branch} {SHA1}\n"
            result = subprocess.run(
                [sys.executable, str(SCRIPT), tmp], input=line.encode("utf-8"), capture_output=True, check=False
            )
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn(branch, result.stdout.decode("utf-8"))
        self.assertNotIn(b"Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
