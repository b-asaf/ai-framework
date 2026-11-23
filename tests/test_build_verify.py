"""build-verify (S.7, DEC-027): the stage runner, the .ai-framework.json reader, scripts/build-verify.py and the wiring."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tools"))

import validate_framework  # noqa: E402
from execution.verification import build_verify  # noqa: E402

SCRIPT = REPO / "scripts" / "build-verify.py"
IMPLEMENTERS = ("api", "backend", "db", "frontend", "frontend-error-fixer", "ui")
NOISY = "i=0; while [ $i -lt 100 ]; do echo line$i; i=$((i+1)); done; exit 1"
SCANNED = ("agents", "commands", "skills", "instructions", "hooks")


def make_repo(parent, name="proj-xyz"):
    root = Path(parent) / name
    subprocess.run(["git", "init", "-q", "--template=", str(root)], check=True, capture_output=True)
    return root


def write_config(root, data):
    text = data if isinstance(data, str) else json.dumps(data)
    (Path(root) / ".ai-framework.json").write_text(text, encoding="utf-8", newline="\n")


class Folder(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)


class ReadCommands(Folder):
    def read(self, data=None):
        if data is not None:
            write_config(self.tmp, data)
        return build_verify.read_commands(self.tmp)

    def test_the_three_commands_are_returned_stripped(self):
        commands, problem = self.read({"lint": " a ", "format": "", "test": "c"})
        self.assertEqual((commands, problem), ({"lint": "a", "format": "", "test": "c"}, None))

    def test_a_missing_key_and_null_are_no_command(self):
        commands, _ = self.read({"test": "t", "lint": None})
        self.assertEqual(commands, {"lint": "", "format": "", "test": "t"})

    def test_a_missing_file_is_a_problem_that_names_the_fix(self):
        commands, problem = self.read()
        self.assertIsNone(commands)
        self.assertTrue(problem[0].startswith(".ai-framework.json not found"))
        self.assertTrue(problem[1])

    def test_unusable_files_are_problems(self):
        cases = (
            ("{bad", "cannot be read"),
            ("[]", "must be a JSON object"),
            ('{"lint": 5}', "must be a string"),
            ('{"maxDiffLines": 400}', "no lint, format or test command"),
            ('{"test": "  "}', "no lint, format or test command"),
        )
        for text, fragment in cases:
            with self.subTest(text=text):
                commands, problem = self.read(text)
                self.assertIsNone(commands)
                self.assertIn(fragment, problem[0])


class RunStages(Folder):
    def setUp(self):
        super().setUp()
        self.root = make_repo(self.tmp)

    def go(self, stages=None, **options):
        commands = {"lint": "", "format": "", "test": ""}
        commands.update(stages or {})
        lines = []
        code = build_verify.run_stages(commands, self.root, out=lines.append, **options)
        return code, "\n".join(lines)

    def test_all_stages_pass(self):
        code, text = self.go({"lint": "true", "test": "true"})
        self.assertEqual(code, 0)
        for fragment in (
            "== LINT: PASS ==", "== FORMAT: SKIPPED (no command configured) ==",
            "== TEST: PASS ==", "== build-verify: ALL STAGES PASS ==",
        ):
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, text)

    def test_the_first_failing_stage_stops_the_run_and_sets_the_code(self):
        order = ("lint", "format", "test")
        for index, failing in enumerate(order):
            with self.subTest(stage=failing):
                stages = {name: "true" for name in order}
                stages[failing] = "exit 7"
                code, text = self.go(stages)
                self.assertEqual(code, index + 1)
                self.assertIn("(exit 7)", text)
                for later in order[index + 1:]:
                    self.assertNotIn(f"== {later.upper()}:", text)

    def test_a_long_failure_is_trimmed_to_the_last_lines(self):
        code, text = self.go({"test": NOISY})
        self.assertEqual(code, 3)
        self.assertIn("showing last 40 of 100 lines", text)
        self.assertIn("line99", text)
        self.assertNotIn("line10", text)

    def test_the_trim_length_and_the_full_flag(self):
        _, text = self.go({"test": NOISY}, trim_lines=5)
        self.assertIn("showing last 5 of 100 lines", text)
        _, text = self.go({"test": NOISY}, full=True)
        self.assertIn("line0", text)
        self.assertNotIn("showing last", text)

    def test_a_short_failure_is_printed_whole(self):
        _, text = self.go({"test": "echo oops; exit 1"})
        self.assertIn("oops", text)
        self.assertNotIn("showing last", text)

    def test_the_log_is_kept_in_the_git_folder_and_the_command_runs_in_the_repository(self):
        _, text = self.go({"test": "pwd; exit 1"})
        self.assertIn(self.root.name, text)
        log = self.root / ".git" / "build-verify-logs" / "test.log"
        self.assertTrue(log.is_file())

    def test_no_shell_is_an_error_that_says_so(self):
        with self.assertRaisesRegex(build_verify.BuildVerifyError, "no shell found"):
            build_verify.find_shell(which=lambda name: None)


class Script(Folder):
    def setUp(self):
        super().setUp()
        self.root = make_repo(self.tmp)

    def run_script(self, *args):
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--repo", str(self.root), *args],
            capture_output=True, encoding="utf-8", errors="replace", stdin=subprocess.DEVNULL,
        )
        return result.returncode, result.stdout, result.stderr

    def test_without_flags_it_uses_the_commands_of_the_config(self):
        write_config(self.root, {"test": "true"})
        code, out, _ = self.run_script()
        self.assertEqual(code, 0)
        self.assertIn("ALL STAGES PASS", out)

    def test_a_failing_config_command_gives_its_stage_code(self):
        write_config(self.root, {"lint": "exit 5"})
        code, out, _ = self.run_script()
        self.assertEqual(code, 1)
        self.assertIn("(exit 5)", out)

    def test_flags_run_only_the_stages_named(self):
        write_config(self.root, {"test": "exit 9"})
        code, out, _ = self.run_script("--lint", "true")
        self.assertEqual(code, 0)
        self.assertNotIn("== TEST: running", out)

    def test_the_full_flag_prints_everything(self):
        _, out, _ = self.run_script("--test", NOISY, "--full")
        self.assertIn("line0", out)

    def test_no_config_and_no_flags_cannot_run(self):
        code, _, err = self.run_script()
        self.assertEqual(code, 4)
        self.assertIn("not found", err)

    def test_a_config_without_commands_cannot_run(self):
        write_config(self.root, {"maxDiffLines": 400})
        code, _, err = self.run_script()
        self.assertEqual(code, 4)
        self.assertIn("no lint, format or test command", err)

    def test_a_bad_flag_is_exit_4_and_not_the_format_code(self):
        code, _, err = self.run_script("--nope")
        self.assertEqual(code, 4)
        self.assertIn("build-verify:", err)


class Wiring(unittest.TestCase):
    def read(self, relative):
        return (REPO / relative).read_text(encoding="utf-8-sig")

    def test_every_implementer_may_run_the_script_by_the_helper_form(self):
        for name in IMPLEMENTERS:
            with self.subTest(agent=name):
                bash = validate_framework.load_agent(REPO / "agents" / f"{name}.md").permission["bash"]
                self.assertEqual(bash.get("python *scripts*build-verify.py*"), "allow")
                self.assertEqual(bash.get("python3 *scripts*build-verify.py*"), "allow")
                self.assertNotIn("hooks/build-verify.sh *", bash)
                self.assertIn('scripts/build-verify.py"', self.read(f"agents/{name}.md"))

    def test_the_skill_calls_the_script(self):
        text = self.read("skills/build-verify/SKILL.md")
        self.assertIn('python "$HOME/.config/opencode/scripts/build-verify.py"', text)
        self.assertIn(".ai-framework.json", text)

    def test_nothing_names_the_retired_script(self):
        paths = [REPO / "AGENTS.md", REPO / "README.md"]
        for folder in SCANNED:
            paths += sorted(path for path in (REPO / folder).rglob("*") if path.is_file())
        found = [
            path.relative_to(REPO).as_posix()
            for path in paths
            if "hooks/build-verify.sh" in path.read_text(encoding="utf-8-sig", errors="replace")
        ]
        self.assertEqual(found, [])

    def test_the_hooks_folder_holds_the_three_launchers_only(self):
        names = sorted(path.name for path in (REPO / "hooks").iterdir())
        self.assertEqual(names, ["commit-msg", "pre-commit", "pre-push"])


if __name__ == "__main__":
    unittest.main()
