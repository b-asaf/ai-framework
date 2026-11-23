"""scripts/diff-size-check.py (DEC-025, S.6c): the measurement behind /oversize, on real temporary git repos."""

import contextlib
import io
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parent.parent
SCRIPT = REPO / "scripts" / "diff-size-check.py"
sys.path.insert(0, str(REPO))

from execution.verification import run as gate  # noqa: E402
from execution.verification.git_runner import run_git  # noqa: E402

TRAILER = "Diff-Size-Approved:"
APPROVAL = f"{TRAILER} 12 the migration cannot be split"
IDENTITY = ["-c", "user.name=Test", "-c", "user.email=test@example.com", "-c", "commit.gpgsign=false"]


class DiffSizeCheck(unittest.TestCase):
    """A temporary repository: main with one commit, and the branch feature/x checked out. The limit is 5."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name).resolve()
        self.gitconfig = self.root / "gitconfig"
        self.gitconfig.write_text("", encoding="utf-8")
        self.repo = self.root / "repo"
        subprocess.run(["git", "init", "-q", "--template=", str(self.repo)], check=True, capture_output=True)
        self.git("symbolic-ref", "HEAD", "refs/heads/main")
        self.write(".ai-framework.json", '{"diffBaseBranch": "main", "maxDiffLines": 5}\n')
        self.commit_all("chore: base")
        self.git("checkout", "-q", "-b", "feature/x")

    def env(self):
        env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_") or k == "GIT_EXEC_PATH"}
        env["GIT_CONFIG_GLOBAL"] = str(self.gitconfig)
        return env

    def git(self, *args):
        result = subprocess.run(["git", "-C", str(self.repo), *IDENTITY, *args], env=self.env(),
                                capture_output=True, encoding="utf-8", errors="replace",
                                stdin=subprocess.DEVNULL)
        if result.returncode != 0:
            self.fail(f"git {' '.join(args)}: {result.stdout}{result.stderr}")
        return result.stdout.strip()

    def write(self, name, text):
        (self.repo / name).write_text(text, encoding="utf-8", newline="")

    def commit_all(self, message):
        self.git("add", ".")
        self.git("commit", "-q", "-m", message)

    def approve(self, line):
        self.git("commit", "-q", "--allow-empty", "-m", "chore: approve a larger branch", "-m", line)

    def big_branch(self, count):
        self.write("big.txt", "".join(f"line {i}\n" for i in range(count)))
        self.commit_all("feat: big change")

    def check(self, script=SCRIPT):
        result = subprocess.run([sys.executable, str(script), "--repo", str(self.repo)], env=self.env(),
                                capture_output=True, encoding="utf-8", errors="replace",
                                stdin=subprocess.DEVNULL)
        fields = dict(line.split(": ", 1) for line in result.stdout.splitlines() if ": " in line)
        return result.returncode, fields

    def lone_script(self):
        folder = self.root / "linked" / "scripts"
        folder.mkdir(parents=True)
        target = folder / "diff-size-check.py"
        shutil.copy2(SCRIPT, target)
        return target

    def gate_blocks(self):
        head = self.git("rev-parse", "HEAD")
        stdin = f"refs/heads/feature/x {head} refs/heads/feature/x {'0' * 40}\n"
        config = {"diffBaseBranch": "main", "maxDiffLines": 5}
        with mock.patch.dict(os.environ, self.env(), clear=True), contextlib.redirect_stdout(io.StringIO()):
            return bool(gate._diff_size_violations(str(self.repo), config, stdin, {}, run_git))

    def test_over_the_limit(self):
        self.big_branch(12)
        code, fields = self.check()
        self.assertEqual(code, 1)
        self.assertEqual(
            (fields["STATUS"], fields["LINES"], fields["LIMIT"], fields["CONFIGURED"], fields["BASE"]),
            ("OVER", "12", "5", "5", "main"),
        )
        self.assertNotIn("APPROVED", fields)
        self.assertIn("exceed", fields["REASON"])

    def test_within_the_limit(self):
        self.big_branch(3)
        code, fields = self.check()
        self.assertEqual((code, fields["STATUS"], fields["LINES"]), (0, "OK", "3"))
        self.assertNotIn("REASON", fields)

    def test_an_approval_raises_the_limit_and_is_reported(self):
        self.big_branch(12)
        self.approve(APPROVAL)
        code, fields = self.check()
        self.assertEqual((code, fields["STATUS"], fields["LIMIT"], fields["APPROVED"]), (0, "OK", "12", "12"))
        self.assertEqual(fields["CONFIGURED"], "5")

    def test_a_branch_that_grew_past_its_approval_is_over_again(self):
        self.big_branch(12)
        self.approve(APPROVAL)
        self.write("more.txt", "one more\n")
        self.commit_all("feat: more")
        code, fields = self.check()
        self.assertEqual((code, fields["STATUS"], fields["LINES"], fields["LIMIT"]), (1, "OVER", "13", "12"))

    def test_a_malformed_approval_is_an_error(self):
        self.big_branch(12)
        self.approve(f"{TRAILER} 12")
        code, fields = self.check()
        self.assertEqual((code, fields["STATUS"]), (2, "ERROR"))
        self.assertIn("malformed approval line", fields["REASON"])

    def test_staged_changes_are_an_error(self):
        self.big_branch(12)
        self.write("staged.txt", "x\n")
        self.git("add", "staged.txt")
        code, fields = self.check()
        self.assertEqual((code, fields["STATUS"]), (2, "ERROR"))
        self.assertIn("staged", fields["REASON"])

    def test_unstaged_and_untracked_files_are_not_in_the_way(self):
        self.big_branch(3)
        self.write("big.txt", "changed\n")
        self.write("new.txt", "x\n")
        code, fields = self.check()
        self.assertEqual((code, fields["STATUS"], fields["LINES"]), (0, "OK", "3"))

    def test_an_unreadable_config_is_an_error(self):
        self.write(".ai-framework.json", "{ not json")
        code, fields = self.check()
        self.assertEqual((code, fields["STATUS"]), (2, "ERROR"))
        self.assertIn(".ai-framework.json cannot be read", fields["REASON"])

    def test_no_base_is_an_error_that_names_the_fix(self):
        self.write(".ai-framework.json", "{}\n")
        code, fields = self.check()
        self.assertEqual((code, fields["STATUS"]), (2, "ERROR"))
        self.assertIn("origin/HEAD is not set", fields["REASON"])

    def test_the_script_and_the_gate_agree(self):
        self.big_branch(12)
        self.assertEqual((self.check()[1]["STATUS"], self.gate_blocks()), ("OVER", True))
        self.approve(APPROVAL)
        self.assertEqual((self.check()[1]["STATUS"], self.gate_blocks()), ("OK", False))
        self.write("more.txt", "one more\n")
        self.commit_all("feat: more")
        self.assertEqual((self.check()[1]["STATUS"], self.gate_blocks()), ("OVER", True))

    def test_the_framework_is_found_through_the_git_setting_when_it_is_not_beside_the_script(self):
        self.big_branch(12)
        self.gitconfig.write_text(f"[aiFramework]\n\troot = {REPO.as_posix()}\n", encoding="utf-8", newline="\n")
        code, fields = self.check(self.lone_script())
        self.assertEqual((code, fields["STATUS"], fields["LINES"]), (1, "OVER", "12"))

    def test_a_missing_framework_is_an_error_that_names_the_fix(self):
        self.big_branch(12)
        code, fields = self.check(self.lone_script())
        self.assertEqual((code, fields["STATUS"]), (2, "ERROR"))
        self.assertIn("setup.py", fields["REASON"])

    def test_the_approval_commit_passes_the_real_commit_hooks(self):
        self.big_branch(12)
        hooks = self.repo / ".git" / "hooks"
        hooks.mkdir(exist_ok=True)
        self.gitconfig.write_text(f"[aiFramework]\n\troot = {REPO.as_posix()}\n", encoding="utf-8", newline="\n")
        for name in ("commit-msg", "pre-commit"):
            shutil.copy2(REPO / "hooks" / name, hooks / name)
        self.approve(APPROVAL)
        code, fields = self.check()
        self.assertEqual((code, fields["STATUS"], fields["APPROVED"]), (0, "OK", "12"))


if __name__ == "__main__":
    unittest.main()
