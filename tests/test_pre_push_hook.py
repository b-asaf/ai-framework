"""Real-git tests for hooks/pre-push, the thin shell edge in front of the Python gate.

Each test builds a local bare remote and a clone, copies the hook into the clone and
runs a real `git push`. The developer's global git config is replaced by a temporary
file (GIT_CONFIG_GLOBAL), so nothing on this machine leaks in or gets changed.
"""
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HOOK_FILES = ("pre-push", "build-verify.sh")
SKIP_VARS = ("SKIP_VERIFICATION", "SKIP_DIFF_SIZE_CHECK", "SKIP_BUILD_VERIFY", "AI_FRAMEWORK_PYTHON")


def clean_env(gitconfig):
    env = {
        k: v for k, v in os.environ.items()
        if k not in SKIP_VARS and not (k.startswith("GIT_") and k != "GIT_EXEC_PATH")
    }
    env.update({
        "GIT_CONFIG_GLOBAL": str(gitconfig),
        "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.com",
        "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.com",
    })
    return env


class PrePushHookTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        gitconfig = self.tmp / "gitconfig"
        gitconfig.write_text("", encoding="utf-8")
        self.env = clean_env(gitconfig)
        self.git("config", "--global", "aiFramework.root", ROOT.as_posix(), cwd=self.tmp)
        self.remote = self.tmp / "remote.git"
        self.git("init", "-q", "--bare", "-b", "main", str(self.remote), cwd=self.tmp)
        seed = self.tmp / "seed"
        seed.mkdir()
        self.git("init", "-q", "-b", "main", cwd=seed)
        (seed / "seed.txt").write_text("seed\n", encoding="utf-8", newline="\n")
        self.git("add", ".", cwd=seed)
        self.git("commit", "-q", "-m", "chore: seed", cwd=seed)
        self.git("push", "-q", str(self.remote), "main", cwd=seed)
        self.clone = self.tmp / "clone"
        self.git("clone", "-q", str(self.remote), str(self.clone), cwd=self.tmp)
        for name in HOOK_FILES:
            target = self.clone / ".git" / "hooks" / name
            shutil.copy2(ROOT / "hooks" / name, target)
            target.chmod(0o755)

    def run_cmd(self, argv, cwd, env=None):
        return subprocess.run(
            argv, cwd=str(cwd), env=env or self.env, stdin=subprocess.DEVNULL,
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )

    def git(self, *args, cwd):
        result = self.run_cmd(["git", *args], cwd)
        if result.returncode != 0:
            self.fail(f"git {' '.join(args)}: {result.stdout}{result.stderr}")
        return result.stdout.strip()

    def push(self, *args, **extra_env):
        result = self.run_cmd(["git", "push", *args], self.clone, {**self.env, **extra_env})
        return result.returncode, result.stdout + result.stderr

    def commit(self, name, text, *messages):
        (self.clone / name).write_text(text, encoding="utf-8", newline="\n")
        self.git("add", name, cwd=self.clone)
        args = [a for m in (messages or ("chore: change",)) for a in ("-m", m)]
        self.git("commit", "-q", *args, cwd=self.clone)

    def start_feature(self, name="feature/x"):
        self.git("checkout", "-q", "-b", name, cwd=self.clone)
        self.commit("notes.txt", "hello\n")

    def write_config(self, text):
        (self.clone / ".ai-framework.json").write_text(text, encoding="utf-8", newline="\n")

    def remote_heads(self):
        out = self.git("ls-remote", "--heads", str(self.remote), cwd=self.tmp)
        return [line.split("\t")[1] for line in out.splitlines()]

    def remote_main(self):
        return self.git("rev-parse", "refs/heads/main", cwd=self.remote)

    def test_plain_feature_push_passes(self):
        self.start_feature()
        code, out = self.push("-u", "origin", "feature/x")
        self.assertEqual(code, 0, out)
        self.assertIn("refs/heads/feature/x", self.remote_heads())

    def test_push_to_default_branch_is_blocked(self):
        self.commit("notes.txt", "hello\n")
        before = self.remote_main()
        code, out = self.push("origin", "main")
        self.assertNotEqual(code, 0, out)
        self.assertIn("branch_protection", out)
        self.assertEqual(self.remote_main(), before)

    def test_skip_verification_does_not_skip_branch_protection(self):
        self.commit("notes.txt", "hello\n")
        before = self.remote_main()
        code, out = self.push("origin", "main", SKIP_VERIFICATION="1")
        self.assertNotEqual(code, 0, out)
        self.assertEqual(self.remote_main(), before)

    def test_configured_protected_branch_is_blocked(self):
        self.write_config('{"protectedBranches": ["temp-dev"]}\n')
        self.start_feature("temp-dev")
        code, out = self.push("-u", "origin", "temp-dev")
        self.assertNotEqual(code, 0, out)
        self.assertNotIn("refs/heads/temp-dev", self.remote_heads())

    def test_dependency_change_needs_the_trailer(self):
        self.git("checkout", "-q", "-b", "feature/dep", cwd=self.clone)
        self.commit("package.json", '{"dependencies": {"left-pad": "1.0.0"}}\n')
        code, out = self.push("-u", "origin", "feature/dep")
        self.assertNotEqual(code, 0, out)
        self.assertIn("dependency_change", out)
        self.assertNotIn("refs/heads/feature/dep", self.remote_heads())
        self.git("commit", "-q", "--amend", "-m", "chore: add left-pad",
                 "-m", "Dependency-Approved: left-pad 1.0.0 reviewed", cwd=self.clone)
        code, out = self.push("-u", "origin", "feature/dep")
        self.assertEqual(code, 0, out)
        self.assertIn("refs/heads/feature/dep", self.remote_heads())

    def test_missing_framework_root_blocks_with_fix_message(self):
        self.git("config", "--global", "--unset", "aiFramework.root", cwd=self.tmp)
        self.start_feature()
        code, out = self.push("-u", "origin", "feature/x")
        self.assertNotEqual(code, 0, out)
        self.assertIn("aiFramework.root", out)
        self.assertNotIn("refs/heads/feature/x", self.remote_heads())

    def test_wrong_framework_root_blocks_with_fix_message(self):
        nowhere = (self.tmp / "nowhere").as_posix()
        self.git("config", "--global", "aiFramework.root", nowhere, cwd=self.tmp)
        self.start_feature()
        code, out = self.push("-u", "origin", "feature/x")
        self.assertNotEqual(code, 0, out)
        self.assertIn("gate script not found", out)

    def test_missing_interpreter_blocks_with_fix_message(self):
        self.start_feature()
        missing = (self.tmp / "no-python").as_posix()
        code, out = self.push("-u", "origin", "feature/x", AI_FRAMEWORK_PYTHON=missing)
        self.assertNotEqual(code, 0, out)
        self.assertIn("no working Python 3", out)
        self.assertNotIn("refs/heads/feature/x", self.remote_heads())

    def test_diff_size_limit_still_blocks(self):
        self.write_config('{"maxDiffLines": 3}\n')
        self.git("checkout", "-q", "-b", "feature/x", cwd=self.clone)
        self.commit("big.txt", "".join(f"line {i}\n" for i in range(10)))
        code, out = self.push("-u", "origin", "feature/x")
        self.assertNotEqual(code, 0, out)
        self.assertIn("atomic-changes limit", out)
        self.assertNotIn("refs/heads/feature/x", self.remote_heads())

    def test_build_verify_failure_still_blocks(self):
        self.write_config('{"test": "exit 1"}\n')
        self.start_feature()
        code, out = self.push("-u", "origin", "feature/x")
        self.assertNotEqual(code, 0, out)
        self.assertIn("build-verify failed", out)
        self.assertNotIn("refs/heads/feature/x", self.remote_heads())


if __name__ == "__main__":
    unittest.main()
