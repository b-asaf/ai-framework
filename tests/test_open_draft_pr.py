"""open-draft-pr.py: a push that the pre-push hook blocks must reach the orchestrator with the hook's own
message, without bypass hints (F71). A push that fails for any other reason keeps its old reason."""

import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPT = REPO / "scripts" / "open-draft-pr.py"

_spec = importlib.util.spec_from_file_location("open_draft_pr", SCRIPT)
open_draft_pr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(open_draft_pr)

GATE_OUTPUT = """BLOCKED dependency_change: dependency manifest changed without an approval trailer: package.json
  Add a Dependency-Approved trailer to the commit, then push again.

ERROR: push gate failed - push blocked (see the lines above).
  Bypass once (reviewed exception only): git push --no-verify

error: failed to push some refs to 'origin'"""


class HookBlockReason(unittest.TestCase):
    def test_the_gate_message_is_kept_without_the_bypass_hints(self):
        reason = open_draft_pr.hook_block_reason(GATE_OUTPUT)
        self.assertTrue(reason.startswith("Blocked by the pre-push hook: "))
        self.assertIn("BLOCKED dependency_change", reason)
        self.assertIn("Dependency-Approved trailer", reason)
        for dropped in ("--no-verify", "see the lines above", "failed to push", "reviewed exception"):
            with self.subTest(dropped=dropped):
                self.assertNotIn(dropped, reason)

    def test_every_blocked_line_is_kept(self):
        text = "BLOCKED branch_protection: first\n  fix one\nBLOCKED dependency_change: second\n  fix two"
        reason = open_draft_pr.hook_block_reason(text)
        for part in ("first", "fix one", "second", "fix two"):
            with self.subTest(part=part):
                self.assertIn(part, reason)

    def test_a_build_verify_failure_keeps_the_test_output(self):
        text = (
            "Running build-verify before push...\nFAIL tests/x.test.js\n  expected 1 to be 2\n\n"
            "ERROR: build-verify failed - push blocked.\n"
            "  Fix the failure above, or SKIP_BUILD_VERIFY=1 git push to override.\n\n"
            "error: failed to push some refs to 'origin'"
        )
        reason = open_draft_pr.hook_block_reason(text)
        self.assertIn("FAIL tests/x.test.js", reason)
        self.assertIn("expected 1 to be 2", reason)
        self.assertNotIn("SKIP_BUILD_VERIFY", reason)

    def test_a_diff_size_block_is_recognised(self):
        text = (
            "ERROR: This branch changes 450 meaningful lines (vs main,\n"
            "  base via config) - exceeds the atomic-changes limit of\n"
            "  400 lines (skills/atomic-changes/SKILL.md).\n"
            "  Split this into smaller PRs, or SKIP_DIFF_SIZE_CHECK=1 git push to\n"
            "  override (only if this size is a deliberate, reviewed exception).\n"
        )
        reason = open_draft_pr.hook_block_reason(text)
        self.assertIn("450 meaningful lines", reason)
        self.assertNotIn("SKIP_DIFF_SIZE_CHECK", reason)
        self.assertNotIn("reviewed exception", reason)

    def test_other_failures_are_not_touched(self):
        for text in (
            "fatal: 'x' does not appear to be a git repository",
            " ! [rejected] a -> a (non-fast-forward)\nerror: failed to push some refs to 'origin'",
            "",
        ):
            with self.subTest(text=text):
                self.assertEqual(open_draft_pr.hook_block_reason(text), "")

    def test_a_long_message_is_cut_with_a_count(self):
        text = "\n".join(["BLOCKED a: x"] + [f"line {n}" for n in range(100)])
        reason = open_draft_pr.hook_block_reason(text)
        self.assertIn("BLOCKED a: x", reason)
        self.assertIn("(+41 more lines)", reason)


def _env():
    env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    env["GIT_TERMINAL_PROMPT"] = "0"
    return env


def git(cwd, *args):
    return subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@example.com", "-c", "commit.gpgsign=false", *args],
        cwd=cwd, env=_env(), check=True, capture_output=True, text=True, encoding="utf-8",
    )


class PushThroughTheScript(unittest.TestCase):
    """Real git, a local bare remote and a hook written by the test."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.template = self.root / "template"
        self.hooks = self.root / "hooks"
        self.bare = self.root / "remote.git"
        self.work = self.root / "work"
        for folder in (self.template, self.hooks, self.work):
            folder.mkdir()
        git(self.root, "init", "--bare", "-b", "main", f"--template={self.template.as_posix()}", str(self.bare))
        git(self.work, "init", "-b", "main", f"--template={self.template.as_posix()}")
        git(self.work, "config", "core.hooksPath", self.hooks.as_posix())
        git(self.work, "remote", "add", "origin", str(self.bare))
        (self.work / "a.txt").write_text("a\n", encoding="utf-8")
        git(self.work, "add", "a.txt")
        git(self.work, "commit", "-m", "chore: first")
        git(self.work, "push", "-u", "origin", "main")
        git(self.work, "checkout", "-b", "fix/x")
        (self.work / "b.txt").write_text("b\n", encoding="utf-8")
        git(self.work, "add", "b.txt")
        git(self.work, "commit", "-m", "fix(x): change b")

    def install_hook(self, body):
        hook = self.hooks / "pre-push"
        hook.write_text("#!/bin/sh\n" + body, encoding="utf-8", newline="\n")
        hook.chmod(0o755)

    def run_script(self):
        result = subprocess.run(
            [sys.executable, "-B", str(SCRIPT)], cwd=self.work, env=_env(),
            capture_output=True, text=True, encoding="utf-8", timeout=120,
        )
        fields = dict(line.split(": ", 1) for line in result.stdout.splitlines() if ": " in line)
        return result, fields

    def test_a_blocked_push_reports_the_hook_message(self):
        self.install_hook(
            "cat > /dev/null\n"
            "echo \"BLOCKED branch_protection: push to protected branch 'main'\"\n"
            "echo \"  Push a feature branch instead.\"\n"
            "echo \"ERROR: push gate failed - push blocked (see the lines above).\"\n"
            "echo \"  Bypass once (reviewed exception only): git push --no-verify\"\n"
            "exit 1\n"
        )
        result, fields = self.run_script()
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertEqual(fields.get("STATUS"), "PUSH_FAILED")
        self.assertIn("BLOCKED branch_protection", fields["REASON"])
        self.assertIn("Push a feature branch instead", fields["REASON"])
        self.assertNotIn("--no-verify", fields["REASON"])

    def test_a_hook_that_writes_to_stderr_is_reported_too(self):
        self.install_hook(
            "cat > /dev/null\n"
            "echo \"BLOCKED dependency_change: package.json changed\" >&2\n"
            "echo \"  Add a Dependency-Approved trailer.\" >&2\n"
            "exit 1\n"
        )
        result, fields = self.run_script()
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertEqual(fields.get("STATUS"), "PUSH_FAILED")
        self.assertIn("BLOCKED dependency_change", fields["REASON"])
        self.assertIn("Dependency-Approved trailer", fields["REASON"])

    def test_another_push_failure_keeps_the_old_reason(self):
        git(self.work, "remote", "set-url", "origin", str(self.root / "does-not-exist.git"))
        result, fields = self.run_script()
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertEqual(fields.get("STATUS"), "PUSH_FAILED")
        self.assertIn("manually to see the full git error", fields["REASON"])
        self.assertNotIn("Blocked by the pre-push hook", fields["REASON"])


if __name__ == "__main__":
    unittest.main()
