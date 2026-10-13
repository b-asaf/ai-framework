import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPT = REPO / "scripts" / "quick-lane-check.py"
IDENTITY = ["-c", "user.name=Test", "-c", "user.email=test@example.com", "-c", "commit.gpgsign=false"]


def git(folder, *args):
    subprocess.run(["git", "-C", str(folder), *IDENTITY, *args], check=True, capture_output=True)


def make_repo(folder, files=None):
    subprocess.run(["git", "init", "-q", "--template=", str(folder)], check=True, capture_output=True)
    write(folder, "app.txt", "one\ntwo\nthree\n")
    for name, text in (files or {}).items():
        write(folder, name, text)
    git(folder, "add", ".")
    git(folder, "commit", "-q", "--no-verify", "-m", "chore: init")


def write(folder, name, text):
    path = Path(folder) / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="")


def check(folder, *args):
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--repo", str(folder), *args],
        capture_output=True, encoding="utf-8", errors="replace",
    )
    fields = dict(line.split(": ", 1) for line in result.stdout.splitlines() if ": " in line)
    return result.returncode, fields


class QuickLaneCheck(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.repo = Path(self.tmp.name)
        make_repo(self.repo, {"b.txt": "b\n", "c.txt": "c\n", "d.txt": "d\n", "e.txt": "e\n"})

    def tearDown(self):
        self.tmp.cleanup()

    def test_start_requires_a_clean_tree(self):
        self.assertEqual(check(self.repo, "--start")[0], 0)
        write(self.repo, "app.txt", "changed\n")
        code, fields = check(self.repo, "--start")
        self.assertEqual(code, 2)
        self.assertEqual(fields["STATUS"], "ERROR")
        self.assertIn("not clean", fields["REASON"])

    def test_a_small_change_is_ok(self):
        write(self.repo, "app.txt", "one\nTWO\nthree\n")
        code, fields = check(self.repo)
        self.assertEqual(code, 0)
        self.assertEqual(fields["STATUS"], "OK")
        self.assertEqual(fields["FILES"], "1")
        self.assertEqual(fields["LINES"], "2")

    def test_no_change_is_ok(self):
        code, fields = check(self.repo)
        self.assertEqual((code, fields["STATUS"], fields["FILES"], fields["LINES"]), (0, "OK", "0", "0"))

    def test_more_than_three_files_is_over(self):
        for name in ("app.txt", "b.txt", "c.txt", "d.txt"):
            write(self.repo, name, "x\n")
        code, fields = check(self.repo)
        self.assertEqual(code, 1)
        self.assertEqual(fields["STATUS"], "OVER")
        self.assertIn("4 files changed (limit 3)", fields["REASON"])

    def test_exactly_three_files_is_ok(self):
        for name in ("app.txt", "b.txt", "c.txt"):
            write(self.repo, name, "x\n")
        self.assertEqual(check(self.repo)[0], 0)

    def test_more_than_sixty_lines_is_over(self):
        write(self.repo, "app.txt", "".join(f"line {i}\n" for i in range(61)))
        code, fields = check(self.repo)
        self.assertEqual(code, 1)
        self.assertIn("lines changed (limit 60)", fields["REASON"])

    def test_untracked_files_count(self):
        write(self.repo, "new.txt", "".join(f"n{i}\n" for i in range(61)))
        code, fields = check(self.repo)
        self.assertEqual(code, 1)
        self.assertEqual(fields["FILES"], "1")
        self.assertEqual(fields["LINES"], "61")

    def test_whitespace_only_changes_are_ignored(self):
        write(self.repo, "app.txt", "one \n two\nthree\n\n")
        code, fields = check(self.repo)
        self.assertEqual(fields["LINES"], "0")
        self.assertEqual(code, 0)

    def test_a_manifest_is_over_even_when_tiny(self):
        write(self.repo, "package.json", "{}\n")
        code, fields = check(self.repo)
        self.assertEqual(code, 1)
        self.assertEqual(fields["RESTRICTED"], "package.json")
        self.assertIn("manifest", fields["REASON"])

    def test_restricted_names_match_in_subfolders(self):
        write(self.repo, "svc/requirements-dev.txt", "x\n")
        write(self.repo, "pkg/yarn.lock", "x\n")
        code, fields = check(self.repo)
        self.assertEqual(code, 1)
        self.assertEqual(fields["RESTRICTED"], "pkg/yarn.lock, svc/requirements-dev.txt")

    def test_a_deleted_file_counts(self):
        (self.repo / "b.txt").unlink()
        code, fields = check(self.repo)
        self.assertEqual((code, fields["FILES"], fields["LINES"]), (0, "1", "1"))

    def test_limits_can_be_set_in_the_project_config(self):
        write(self.repo, ".ai-framework.json", json.dumps({"quickLane": {"maxFiles": 1, "maxLines": 5}}))
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-q", "--no-verify", "-m", "chore: config")
        write(self.repo, "app.txt", "x\n")
        write(self.repo, "b.txt", "y\n")
        code, fields = check(self.repo)
        self.assertEqual(code, 1)
        self.assertEqual(fields["LIMITS"], "files 1, lines 5")

    def test_limits_can_be_set_on_the_command_line(self):
        write(self.repo, "app.txt", "x\n")
        write(self.repo, "b.txt", "y\n")
        code, fields = check(self.repo, "--max-files", "1")
        self.assertEqual(code, 1)
        self.assertIn("2 files changed (limit 1)", fields["REASON"])

    def test_a_bad_config_fails_closed(self):
        write(self.repo, ".ai-framework.json", '{"quickLane": {"maxFiles": "three"}}')
        code, fields = check(self.repo)
        self.assertEqual(code, 2)
        self.assertEqual(fields["STATUS"], "ERROR")

    def test_a_folder_that_is_not_a_repo_is_an_error(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as folder:
            code, fields = check(folder)
            self.assertEqual((code, fields["STATUS"]), (2, "ERROR"))

    def test_a_repo_without_commits_is_an_error(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as folder:
            subprocess.run(["git", "init", "-q", "--template=", folder], check=True, capture_output=True)
            code, fields = check(folder)
            self.assertEqual((code, fields["STATUS"]), (2, "ERROR"))


if __name__ == "__main__":
    unittest.main()
