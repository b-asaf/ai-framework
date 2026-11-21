"""The reviewed override of the changed-lines limit (DEC-025, S.6b): the Diff-Size-Approved line."""

import contextlib
import io
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from execution.verification import run as gate  # noqa: E402
from execution.verification.checks import diff_size  # noqa: E402
from execution.verification.git_runner import run_git  # noqa: E402

SHA = "a" * 40
TRAILER = "Diff-Size-Approved:"


def fake_git(answers):
    def run(argv):
        if argv[0] not in answers:
            raise diff_size.DiffSizeError(f"git {argv} failed")
        return answers[argv[0]]

    return run


class ParseApprovalLines(unittest.TestCase):
    def parse(self, message):
        return diff_size.parse_approval_lines(message)

    def test_a_valid_line_gives_its_number(self):
        message = f"feat: x\n\n{TRAILER} 650 the schema change cannot be split\n"
        self.assertEqual(self.parse(message), ([650], []))

    def test_surrounding_space_and_a_tab_are_fine(self):
        self.assertEqual(self.parse(f"  {TRAILER}\t12\treviewed  \n"), ([12], []))

    def test_every_valid_line_of_a_message_counts(self):
        self.assertEqual(self.parse(f"{TRAILER} 10 first\n{TRAILER} 30 second\n"), ([10, 30], []))

    def test_words_in_the_middle_of_a_line_are_ignored(self):
        self.assertEqual(self.parse(f"see {TRAILER} 12 elsewhere in a sentence"), ([], []))

    def test_malformed_lines_are_reported(self):
        lines = (
            TRAILER, f"{TRAILER} 650", f"{TRAILER}   ", f"{TRAILER} many why", f"{TRAILER} 0 why",
            f"{TRAILER} -5 why", f"{TRAILER} 6.5 why", f"{TRAILER} \u00b2 why", f"{TRAILER} 1234567890 why",
        )
        for line in lines:
            with self.subTest(line=line):
                self.assertEqual(self.parse(line + "\n"), ([], [line.strip()]))


class FindViolationsWithApprovals(unittest.TestCase):
    def test_an_approval_raises_the_limit_of_its_branch(self):
        self.assertEqual(diff_size.find_violations([("b", 500, "origin/main")], 400, {"b": 500}), [])

    def test_over_the_approved_number_is_a_violation_that_says_so(self):
        found = diff_size.find_violations([("b", 501, "origin/main")], 400, {"b": 500})
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["check"], "diff_size")
        self.assertIn("limit of 500 lines", found[0]["reason"])
        self.assertIn("raised to 500 by a Diff-Size-Approved line", found[0]["reason"])

    def test_an_approval_below_the_limit_changes_nothing(self):
        found = diff_size.find_violations([("b", 401, "origin/main")], 400, {"b": 100})
        self.assertEqual(len(found), 1)
        self.assertIn("limit of 400 lines", found[0]["reason"])
        self.assertNotIn("raised", found[0]["reason"])

    def test_an_approval_of_another_branch_does_not_apply(self):
        found = diff_size.find_violations([("b", 401, "origin/main")], 400, {"other": 900})
        self.assertEqual(len(found), 1)


class ReadApprovalsWithFakeGit(unittest.TestCase):
    def test_a_deleted_branch_needs_no_git(self):
        self.assertEqual(diff_size.read_approvals("0" * 40, "origin/main", run_git=fake_git({})), (0, []))

    def test_the_largest_number_wins_and_a_bad_line_names_its_commit(self):
        log = (
            SHA + "\x00feat: x\n\n" + TRAILER + " 7 first\n\x03\n"
            + "b" * 40 + "\x00chore: y\n\n" + TRAILER + " 20 second\n" + TRAILER + " x broken\n\x03\n"
        )
        git = fake_git({"merge-base": "abc123\n", "log": log})
        approved, problems = diff_size.read_approvals(SHA, "origin/main", run_git=git)
        self.assertEqual(approved, 20)
        self.assertEqual(len(problems), 1)
        self.assertIn("bbbbbbbb", problems[0])
        self.assertIn(TRAILER + " x broken", problems[0])


class RealRepo(unittest.TestCase):
    """A temporary repository: main with one commit, and the branch feature/x checked out."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name).resolve()
        self.repo = root / "repo"
        self.repo.mkdir()
        gitconfig = root / "gitconfig"
        gitconfig.write_text("[user]\n\tname = t\n\temail = t@example.com\n", encoding="utf-8", newline="\n")
        env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_") or k == "GIT_EXEC_PATH"}
        env["GIT_CONFIG_GLOBAL"] = str(gitconfig)
        patcher = mock.patch.dict(os.environ, env, clear=True)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.git("init", "-q")
        self.git("symbolic-ref", "HEAD", "refs/heads/main")
        self.commit_file("base.txt", "base\n", "chore: base")
        self.git("checkout", "-q", "-b", "feature/x")

    def git(self, *args):
        result = subprocess.run(["git", *args], cwd=str(self.repo), capture_output=True, text=True,
                                encoding="utf-8", errors="replace", stdin=subprocess.DEVNULL)
        if result.returncode != 0:
            self.fail(f"git {' '.join(args)}: {result.stdout}{result.stderr}")
        return result.stdout.strip()

    def dgit(self, argv):
        return run_git(argv, cwd=str(self.repo), error=diff_size.DiffSizeError)

    def head(self):
        return self.git("rev-parse", "HEAD")

    def commit(self, message, *paragraphs):
        args = ["commit", "-q", "-m", message]
        for paragraph in paragraphs:
            args += ["-m", paragraph]
        self.git(*args)

    def commit_file(self, name, text, message, *paragraphs):
        (self.repo / name).write_text(text, encoding="utf-8", newline="\n")
        self.git("add", name)
        self.commit(message, *paragraphs)

    def approve(self, line):
        self.git("commit", "-q", "--allow-empty", "-m", "chore: approve a larger branch", "-m", line)

    def big_branch(self, count):
        self.commit_file("big.txt", "".join(f"line {i}\n" for i in range(count)), "feat: big change")

    def result(self, limit=5):
        head = self.head()
        lines = diff_size.measure(head, "main", run_git=self.dgit)
        approved, problems = diff_size.read_approvals(head, "main", run_git=self.dgit)
        found = diff_size.find_violations([("feature/x", lines, "main")], limit, {"feature/x": approved})
        return lines, approved, problems, found


class RealGitApproval(RealRepo):
    def test_a_branch_without_a_line_is_over_the_limit(self):
        self.big_branch(12)
        lines, approved, problems, found = self.result()
        self.assertEqual((lines, approved, problems), (12, 0, []))
        self.assertEqual(len(found), 1)

    def test_a_line_passes_the_branch_up_to_its_number(self):
        self.big_branch(12)
        self.approve(f"{TRAILER} 12 the migration cannot be split")
        self.assertEqual(self.result(), (12, 12, [], []))

    def test_a_branch_that_grows_past_its_number_is_blocked_again(self):
        self.big_branch(12)
        self.approve(f"{TRAILER} 12 the migration cannot be split")
        self.commit_file("more.txt", "one more\n", "feat: more")
        lines, approved, _problems, found = self.result()
        self.assertEqual((lines, approved), (13, 12))
        self.assertEqual(len(found), 1)
        self.assertIn("limit of 12 lines", found[0]["reason"])
        self.assertIn("raised to 12", found[0]["reason"])

    def test_an_approval_made_before_later_commits_still_counts(self):
        self.big_branch(8)
        self.approve(f"{TRAILER} 12 four more lines are needed")
        self.commit_file("more.txt", "a\nb\nc\nd\n", "feat: more")
        self.assertEqual(self.result(), (12, 12, [], []))

    def test_a_malformed_line_is_reported_with_its_commit(self):
        for line in (TRAILER + " 12", TRAILER + " many because", TRAILER + " 0 because"):
            with self.subTest(line=line):
                self.git("checkout", "-q", "-B", "feature/x", "main")
                self.big_branch(12)
                self.approve(line)
                _lines, approved, problems, found = self.result()
                self.assertEqual(approved, 0)
                self.assertEqual(len(problems), 1)
                self.assertIn(self.head()[:8], problems[0])
                self.assertIn(line, problems[0])
                self.assertEqual(len(found), 1)

    def test_one_valid_and_one_malformed_line(self):
        self.big_branch(12)
        self.approve(f"{TRAILER} 30 fine")
        self.approve(f"{TRAILER} broken")
        _lines, approved, problems, _found = self.result()
        self.assertEqual((approved, len(problems)), (30, 1))

    def test_a_line_on_the_base_branch_does_not_count(self):
        self.git("checkout", "-q", "main")
        self.commit_file("m.txt", "m\n", "chore: m", f"{TRAILER} 999 old approval on the base branch")
        self.git("checkout", "-q", "-B", "feature/x")
        self.big_branch(12)
        lines, approved, problems, found = self.result()
        self.assertEqual((approved, problems), (0, []))
        self.assertEqual(len(found), 1)


class Wiring(RealRepo):
    def violations(self, env=None):
        stdin = f"refs/heads/feature/x {self.head()} refs/heads/feature/x {'0' * 40}\n"
        config = {"diffBaseBranch": "main", "maxDiffLines": 5}
        with contextlib.redirect_stdout(io.StringIO()):
            return gate._diff_size_violations(str(self.repo), config, stdin, env or {}, run_git)

    def test_over_the_limit_without_a_line_is_blocked(self):
        self.big_branch(12)
        found = self.violations()
        self.assertEqual([v["check"] for v in found], ["diff_size"])
        self.assertIn("limit of 5 lines", found[0]["reason"])

    def test_a_line_lets_the_branch_through_up_to_its_number(self):
        self.big_branch(12)
        self.approve(f"{TRAILER} 12 the migration cannot be split")
        self.assertEqual(self.violations(), [])

    def test_a_branch_over_its_approved_number_is_blocked(self):
        self.big_branch(12)
        self.approve(f"{TRAILER} 12 the migration cannot be split")
        self.commit_file("more.txt", "one more\n", "feat: more")
        found = self.violations()
        self.assertEqual(len(found), 1)
        self.assertIn("raised to 12", found[0]["reason"])

    def test_a_malformed_line_blocks_even_a_small_branch(self):
        self.big_branch(3)
        self.approve(f"{TRAILER} 12")
        found = self.violations()
        self.assertEqual(len(found), 1)
        self.assertIn("feature/x", found[0]["reason"])
        self.assertIn("malformed approval line", found[0]["reason"])

    def test_the_skip_variable_still_skips(self):
        self.big_branch(12)
        self.assertEqual(self.violations({"SKIP_DIFF_SIZE_CHECK": "1"}), [])


if __name__ == "__main__":
    unittest.main()
