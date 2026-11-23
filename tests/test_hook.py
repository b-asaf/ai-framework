"""The git hooks as Python (S.7, DEC-027): commit-msg, pre-commit, the edge script and the launcher on real git."""

import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from execution.verification import hook  # noqa: E402
from execution.verification.git_runner import GitError  # noqa: E402

HOOKS = ("pre-commit", "commit-msg", "pre-push")
SKIP_VARS = ("SKIP_VERIFICATION", "SKIP_DIFF_SIZE_CHECK", "SKIP_BUILD_VERIFY", "AI_FRAMEWORK_PYTHON")


def fake_git(head, origin=None):
    def run(argv, cwd=None, *, error=GitError):
        if argv == ["symbolic-ref", "--short", "HEAD"]:
            if head is None:
                raise error("detached HEAD")
            return head + "\n"
        if argv == ["symbolic-ref", "--short", "refs/remotes/origin/HEAD"]:
            if origin is None:
                raise error("no origin/HEAD")
            return origin + "\n"
        raise error(f"unexpected git call {argv}")

    return run


def captured(call):
    with contextlib.redirect_stdout(io.StringIO()) as out:
        code = call()
    return code, out.getvalue()


class CommitMsg(unittest.TestCase):
    def check(self, text):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "MSG"
            path.write_text(text, encoding="utf-8", newline="\n")
            return captured(lambda: hook.commit_msg(str(path)))

    def test_conventional_messages_pass(self):
        good = (
            "feat: add export\n", "fix(api): handle null\n\nbody text\n", "# a comment\n\nchore: tidy\n",
            "docs: x\n\nDiff-Size-Approved: 12 because\n", "feat: " + "x" * 100 + "\n",
        )
        for text in good:
            with self.subTest(text=text):
                self.assertEqual(self.check(text)[0], 0)

    def test_other_messages_are_blocked(self):
        bad = ("", "\n", "wip\n", "Feat: x\n", "feat:x\n", "feat(): x\n", "feat: " + "x" * 101 + "\n")
        for text in bad:
            with self.subTest(text=text):
                code, out = self.check(text)
                self.assertEqual(code, 1)
                self.assertIn("BLOCKED commit-msg", out)

    def test_only_the_first_line_counts(self):
        code, out = self.check("wip\n\nfeat: fine on the second line\n")
        self.assertEqual(code, 1)
        self.assertIn("Your first line: wip", out)

    def test_a_message_file_that_cannot_be_read_is_blocked(self):
        code, out = captured(lambda: hook.commit_msg(str(ROOT / "no-such-folder" / "MSG")))
        self.assertEqual(code, 1)
        self.assertIn("cannot be read", out)


class PreCommit(unittest.TestCase):
    def check(self, head, origin=None, config=None):
        with tempfile.TemporaryDirectory() as tmp:
            if config is not None:
                text = config if isinstance(config, str) else json.dumps(config)
                (Path(tmp) / ".ai-framework.json").write_text(text, encoding="utf-8", newline="\n")
            return captured(lambda: hook.pre_commit(tmp, fake_git(head, origin)))

    def test_without_a_remote_the_old_list_applies(self):
        for branch in ("main", "master", "develop"):
            with self.subTest(branch=branch):
                code, out = self.check(branch)
                self.assertEqual(code, 1)
                self.assertIn("BLOCKED pre-commit", out)
                self.assertIn(branch, out)
        for branch in ("feature/x", "fix/y"):
            with self.subTest(branch=branch):
                self.assertEqual(self.check(branch)[0], 0)

    def test_the_default_branch_of_the_remote_is_protected_instead_of_the_old_list(self):
        self.assertEqual(self.check("trunk", "origin/trunk")[0], 1)
        self.assertEqual(self.check("main", "origin/trunk")[0], 0)

    def test_configured_branches_are_added(self):
        config = {"protectedBranches": ["release/*"]}
        self.assertEqual(self.check("release/1", "origin/main", config)[0], 1)
        self.assertEqual(self.check("feature/x", "origin/main", config)[0], 0)
        self.assertEqual(self.check("temp-dev", None, {"protectedBranches": ["temp-dev"]})[0], 1)

    def test_a_config_that_cannot_be_read_falls_back_to_the_old_list(self):
        self.assertEqual(self.check("main", None, "{bad")[0], 1)

    def test_a_detached_head_is_not_blocked(self):
        self.assertEqual(self.check(None)[0], 0)


class Dispatch(unittest.TestCase):
    def test_an_unknown_hook_is_blocked(self):
        code, out = captured(lambda: hook.main(["hook.py", "nope"], "", {}, fake_git("main")))
        self.assertEqual(code, 1)
        self.assertIn("unknown hook", out)

    def test_an_unexpected_error_is_a_readable_block(self):
        def boom(argv, cwd=None, *, error=GitError):
            raise RuntimeError("boom")

        code, out = captured(lambda: hook.main_or_block(["hook.py", "pre-commit"], "", {}, boom))
        self.assertEqual(code, 1)
        self.assertIn("internal error: RuntimeError: boom", out)

    def test_the_edge_script_runs_as_a_script_from_any_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            message = Path(tmp) / "MSG"
            for text, expected in (("feat: ok\n", 0), ("wip\n", 1)):
                message.write_text(text, encoding="utf-8", newline="\n")
                result = subprocess.run(
                    [sys.executable, "-B", str(ROOT / "execution" / "verification" / "hook.py"), "commit-msg", str(message)],
                    cwd=tmp, capture_output=True, text=True, stdin=subprocess.DEVNULL,
                )
                self.assertEqual(result.returncode, expected, result.stdout + result.stderr)


class Launchers(unittest.TestCase):
    """The launcher on real git: three files, a temporary global git config, a repository without the framework template."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name).resolve()
        self.gitconfig = self.tmp / "gitconfig"
        self.write_gitconfig(root=True)
        self.env = {
            k: v for k, v in os.environ.items()
            if k not in SKIP_VARS and not (k.startswith("GIT_") and k != "GIT_EXEC_PATH")
        }
        self.env["GIT_CONFIG_GLOBAL"] = str(self.gitconfig)
        self.repo = self.tmp / "repo"
        self.git(self.tmp, "init", "-q", "--template=", "-b", "main", str(self.repo))
        folder = self.repo / ".git" / "hooks"
        folder.mkdir(exist_ok=True)
        for name in HOOKS:
            shutil.copy2(ROOT / "hooks" / name, folder / name)
            (folder / name).chmod(0o755)
        (self.repo / "a.txt").write_text("a\n", encoding="utf-8", newline="\n")
        self.git(self.repo, "add", ".")
        self.git(self.repo, "commit", "-q", "--no-verify", "-m", "chore: init")

    def write_gitconfig(self, root):
        text = "[user]\n\tname = t\n\temail = t@example.com\n"
        if root:
            text += f"[aiFramework]\n\troot = {ROOT.as_posix()}\n"
        self.gitconfig.write_text(text, encoding="utf-8", newline="\n")

    def git(self, cwd, *args, env=None):
        result = subprocess.run(
            ["git", *args], cwd=str(cwd), env=env or self.env, stdin=subprocess.DEVNULL,
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        return result

    def commit(self, *messages, flags=(), env=None):
        (self.repo / "b.txt").write_text("b\n", encoding="utf-8", newline="\n")
        self.git(self.repo, "add", "b.txt")
        args = ["commit", "-q", *flags]
        for message in messages:
            args += ["-m", message]
        result = self.git(self.repo, *args, env=env)
        return result.returncode, result.stdout + result.stderr

    def count(self):
        return int(self.git(self.repo, "rev-list", "--count", "HEAD").stdout.strip())

    def feature(self):
        self.git(self.repo, "checkout", "-q", "-b", "feature/x")

    def test_a_commit_on_main_is_blocked(self):
        code, out = self.commit("chore: x")
        self.assertNotEqual(code, 0, out)
        self.assertIn("BLOCKED pre-commit", out)
        self.assertEqual(self.count(), 1)

    def test_a_commit_on_main_with_no_verify_is_allowed(self):
        code, out = self.commit("chore: x", flags=("--no-verify",))
        self.assertEqual(code, 0, out)

    def test_a_feature_commit_with_a_good_message_passes(self):
        self.feature()
        code, out = self.commit("feat: x")
        self.assertEqual(code, 0, out)
        self.assertEqual(self.count(), 2)

    def test_a_bad_message_is_blocked(self):
        self.feature()
        code, out = self.commit("wip")
        self.assertNotEqual(code, 0, out)
        self.assertIn("BLOCKED commit-msg", out)
        self.assertEqual(self.count(), 1)

    def test_a_wrong_first_line_is_blocked_even_when_a_later_line_is_fine(self):
        self.feature()
        code, out = self.commit("wip", "feat: second paragraph")
        self.assertNotEqual(code, 0, out)
        self.assertIn("BLOCKED commit-msg", out)

    def test_a_missing_framework_root_blocks_with_a_fix(self):
        self.feature()
        self.write_gitconfig(root=False)
        code, out = self.commit("feat: x")
        self.assertNotEqual(code, 0, out)
        self.assertIn("aiFramework.root", out)
        self.assertEqual(self.count(), 1)

    def test_a_missing_python_blocks_with_a_fix(self):
        self.feature()
        env = dict(self.env, AI_FRAMEWORK_PYTHON=(self.tmp / "no-python").as_posix())
        code, out = self.commit("feat: x", env=env)
        self.assertNotEqual(code, 0, out)
        self.assertIn("no working Python 3", out)

    def test_the_three_hooks_are_one_file_with_unix_line_endings(self):
        first = (ROOT / "hooks" / HOOKS[0]).read_bytes()
        for name in HOOKS:
            with self.subTest(hook=name):
                data = (ROOT / "hooks" / name).read_bytes()
                self.assertEqual(data, first)
                self.assertNotIn(b"\r", data)


if __name__ == "__main__":
    unittest.main()
