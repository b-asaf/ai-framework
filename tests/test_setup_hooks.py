"""Tests for the hook wiring in setup.py: template copies, aiFramework.root, --install-hooks.

Every test runs with GIT_CONFIG_GLOBAL pointing at a temporary file and with setup.REPO and
setup.HOOKS pointing at a temporary copy of hooks/, so the developer's git config and the
real git-template folder are never touched.
"""
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
sys.path.insert(0, str(REPO / "tools"))
sys.path.insert(0, str(REPO))

import setup as framework_setup  # noqa: E402

NAMES = framework_setup.HOOK_NAMES


class SetupHooksCase(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name).resolve()
        self.gitconfig = self.tmp / "gitconfig"
        self.gitconfig.write_text("[user]\n\tname = t\n\temail = t@example.com\n",
                                  encoding="utf-8", newline="\n")
        self.fw = self.tmp / "framework"
        (self.fw / "hooks").mkdir(parents=True)
        for name in NAMES:
            shutil.copy2(REPO / "hooks" / name, self.fw / "hooks" / name)
        env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_") or k == "GIT_EXEC_PATH"}
        env["GIT_CONFIG_GLOBAL"] = str(self.gitconfig)
        for patcher in (
            mock.patch.dict(os.environ, env, clear=True),
            mock.patch.object(framework_setup, "REPO", self.fw),
            mock.patch.object(framework_setup, "HOOKS", self.fw / "hooks"),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)

    def run_git(self, cwd, *args):
        return subprocess.run(["git", *args], cwd=str(cwd), capture_output=True, text=True,
                              encoding="utf-8", errors="replace", stdin=subprocess.DEVNULL)

    def git(self, cwd, *args):
        result = self.run_git(cwd, *args)
        if result.returncode != 0:
            self.fail(f"git {' '.join(args)}: {result.stdout}{result.stderr}")
        return result.stdout.strip()

    def set_global(self, key, value):
        self.git(self.tmp, "config", "--global", key, value)

    def global_value(self, key):
        result = self.run_git(self.tmp, "config", "--global", "--get", key)
        return result.stdout.strip() if result.returncode == 0 else None

    def quiet(self, func, *args):
        with contextlib.redirect_stdout(io.StringIO()) as out:
            result = func(*args)
        return result, out.getvalue()

    def make_repo(self, name):
        path = self.tmp / name
        path.mkdir()
        self.git(path, "init", "-q", "-b", "main")
        return path

    def same_bytes(self, folder, name):
        return (folder / name).read_bytes() == (self.fw / "hooks" / name).read_bytes()


class TemplateTest(SetupHooksCase):
    def test_template_gets_plain_copies_and_no_bak_files(self):
        hooks = self.fw / "git-template" / "hooks"
        hooks.mkdir(parents=True)
        os.link(self.fw / "hooks" / "pre-push", hooks / "pre-push")
        (hooks / "pre-push.bak").write_text("old\n", newline="\n")
        self.quiet(framework_setup.add_git_template)
        self.assertEqual(sorted(p.name for p in hooks.iterdir()), sorted(NAMES))
        for name in NAMES:
            self.assertTrue(self.same_bytes(hooks, name), name)
            self.assertFalse(os.path.samefile(hooks / name, self.fw / "hooks" / name), name)
        self.assertEqual(Path(self.global_value("init.templateDir")), self.fw / "git-template")


class FrameworkRootTest(SetupHooksCase):
    def test_root_is_recorded_with_forward_slashes_and_removed_again(self):
        self.quiet(framework_setup.set_framework_root)
        self.assertEqual(self.global_value("aiFramework.root"), self.fw.as_posix())
        self.quiet(framework_setup.unset_framework_root)
        self.assertIsNone(self.global_value("aiFramework.root"))

    def test_unset_leaves_a_root_that_points_elsewhere(self):
        self.set_global("aiFramework.root", "elsewhere")
        self.quiet(framework_setup.unset_framework_root)
        self.assertEqual(self.global_value("aiFramework.root"), "elsewhere")

    def test_a_worktree_does_not_record_a_root(self):
        (self.fw / ".git").write_text("gitdir: elsewhere\n", newline="\n")
        self.quiet(framework_setup.set_framework_root)
        self.assertIsNone(self.global_value("aiFramework.root"))


class InstallHooksTest(SetupHooksCase):
    def test_installs_every_hook_and_a_second_run_changes_nothing(self):
        repo = self.make_repo("proj")
        hooks = repo / ".git" / "hooks"
        done, _ = self.quiet(framework_setup.install_hooks, str(repo))
        self.assertTrue(done)
        for name in NAMES:
            self.assertTrue(self.same_bytes(hooks, name), name)
        _, text = self.quiet(framework_setup.install_hooks, str(repo))
        self.assertIn("already up to date", text)
        self.assertEqual(list(hooks.glob("*.bak")), [])

    def test_a_differing_hook_is_saved_once_as_bak(self):
        repo = self.make_repo("proj")
        target = repo / ".git" / "hooks" / "pre-push"
        bak = target.with_name("pre-push.bak")
        target.write_text("# mine\n", newline="\n")
        self.quiet(framework_setup.install_hooks, str(repo))
        self.assertEqual(bak.read_text(), "# mine\n")
        target.write_text("# other\n", newline="\n")
        self.quiet(framework_setup.install_hooks, str(repo))
        self.assertEqual(bak.read_text(), "# mine\n")
        self.assertTrue(self.same_bytes(target.parent, "pre-push"))

    def test_refuses_when_hooks_path_is_set(self):
        repo = self.make_repo("proj")
        self.git(repo, "config", "core.hooksPath", ".husky")
        done, text = self.quiet(framework_setup.install_hooks, str(repo))
        self.assertFalse(done)
        self.assertIn("core.hooksPath", text)
        self.assertFalse((repo / ".git" / "hooks" / "pre-push").exists())

    def test_refuses_a_folder_that_is_not_a_repository(self):
        folder = self.tmp / "plain"
        folder.mkdir()
        done, _ = self.quiet(framework_setup.install_hooks, str(folder))
        self.assertFalse(done)


class VerifyTest(SetupHooksCase):
    def test_stale_hooks_lists_missing_and_changed_files(self):
        folder = self.tmp / "copy"
        folder.mkdir()
        for name in NAMES[:3]:
            shutil.copy2(self.fw / "hooks" / name, folder / name)
        (folder / NAMES[0]).write_text("changed\n", newline="\n")
        self.assertEqual(framework_setup._stale_hooks(folder), [NAMES[0], NAMES[3]])

    def test_hook_python_finds_a_python_3(self):
        self.assertIsNotNone(framework_setup._hook_python())


class FreshCloneTest(SetupHooksCase):
    def test_a_fresh_clone_gets_the_hook_and_a_push_to_main_is_blocked(self):
        remote = self.tmp / "remote.git"
        self.git(self.tmp, "init", "-q", "--bare", "-b", "main", str(remote))
        seed = self.make_repo("seed")
        (seed / "a.txt").write_text("a\n", newline="\n")
        self.git(seed, "add", ".")
        self.git(seed, "commit", "-q", "-m", "chore: seed")
        self.git(seed, "push", "-q", str(remote), "main")
        self.quiet(framework_setup.add_git_template)
        self.set_global("aiFramework.root", REPO.as_posix())  # the real gate script lives there
        clone = self.tmp / "clone"
        self.git(self.tmp, "clone", "-q", str(remote), str(clone))
        self.assertTrue(self.same_bytes(clone / ".git" / "hooks", "pre-push"))
        (clone / "b.txt").write_text("b\n", newline="\n")
        self.git(clone, "add", ".")
        self.git(clone, "commit", "-q", "--no-verify", "-m", "chore: b")
        before = self.git(remote, "rev-parse", "refs/heads/main")
        push = self.run_git(clone, "push", "origin", "main")
        output = push.stdout + push.stderr
        self.assertNotEqual(push.returncode, 0, output)
        self.assertIn("BLOCKED", output)
        self.assertEqual(self.git(remote, "rev-parse", "refs/heads/main"), before)


if __name__ == "__main__":
    unittest.main()
