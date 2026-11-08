import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from execution.runner import facts  # noqa: E402


def py(code):
    return [sys.executable, "-c", code]


class CommandArgv(unittest.TestCase):
    def test_a_plain_command_is_split_and_quotes_group(self):
        self.assertEqual(facts.command_argv('node --test "src dir"'), ["node", "--test", "src dir"])

    def test_shell_syntax_is_rejected_not_interpreted(self):
        for text in ("npm test && npm run lint", "npm test | tail", "cd web; npm test", "npm test > out", "echo $HOME", "a\nb", "run\\x"):
            with self.subTest(text=text), self.assertRaises(facts.FactsError):
                facts.command_argv(text)

    def test_empty_and_unbalanced_commands_are_rejected(self):
        for text in ("", "   ", None, 'node "x'):
            with self.subTest(text=text), self.assertRaises(facts.FactsError):
                facts.command_argv(text)


class TestCommand(unittest.TestCase):
    def read(self, content):
        with tempfile.TemporaryDirectory() as tmp:
            if content is not None:
                (Path(tmp) / ".ai-framework.json").write_text(content, encoding="utf-8")
            return facts.test_command(tmp)

    def test_the_test_key_is_returned_trimmed(self):
        self.assertEqual(self.read(json.dumps({"test": " node --test "})), "node --test")

    def test_everything_else_fails_closed(self):
        for content in (None, "not json", "[]", "{}", '{"test": ""}', '{"test": 5}'):
            with self.subTest(content=content), self.assertRaises(facts.FactsError):
                self.read(content)


class ResolveArgv(unittest.TestCase):
    def test_a_name_is_looked_up_on_the_path(self):
        found = facts.resolve_argv(["npm", "test"], ".", which=lambda name: "/bin/" + name)
        self.assertEqual(found, ["/bin/npm", "test"])

    def test_an_unknown_name_fails(self):
        with self.assertRaises(facts.FactsError):
            facts.resolve_argv(["nope"], ".", which=lambda name: None)

    def test_a_path_is_resolved_against_the_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "gradlew").write_text("x", encoding="utf-8")
            self.assertEqual(facts.resolve_argv(["./gradlew", "test"], tmp), [str(Path(tmp) / "gradlew"), "test"])
            with self.assertRaises(facts.FactsError):
                facts.resolve_argv(["./missing"], tmp)


class RunTests(unittest.TestCase):
    def run_code(self, code, **options):
        with tempfile.TemporaryDirectory() as tmp:
            return facts.run_tests(py(code), tmp, **options)

    def test_a_passing_run(self):
        result = self.run_code("print('ok')")
        self.assertTrue(result.passed)
        self.assertEqual((result.exit_code, result.tail), (0, ("ok",)))

    def test_a_failing_run_keeps_the_exit_code_and_merges_both_streams(self):
        result = self.run_code("import sys; print('out'); print('err', file=sys.stderr); sys.exit(3)")
        self.assertFalse(result.passed)
        self.assertEqual(result.exit_code, 3)
        self.assertEqual(sorted(result.tail), ["err", "out"])

    def test_a_long_output_is_cut_to_the_last_lines(self):
        result = self.run_code("for i in range(100): print(i)")
        self.assertEqual((len(result.tail), result.total_lines, result.tail[-1]), (facts.TAIL_LINES, 100, "99"))

    def test_a_timeout_is_a_result(self):
        result = self.run_code("import time; time.sleep(30)", timeout=1)
        self.assertTrue(result.timed_out)
        self.assertFalse(result.passed)
        self.assertIn("1 s", result.note)

    def test_a_command_that_cannot_start_is_a_result(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = facts.run_tests([str(Path(tmp) / "missing-program")], tmp)
        self.assertEqual(result.exit_code, -1)
        self.assertFalse(result.passed)
        self.assertIn("could not start", result.note)

    def test_no_stdin_and_no_shell(self):
        seen = {}

        def fake(argv, **kwargs):
            seen.update(kwargs, argv=argv)
            return subprocess.CompletedProcess(argv, 0, stdout="fine\n", stderr=None)

        facts.run_tests(["x", "y"], ".", runner=fake)
        self.assertIs(seen["stdin"], subprocess.DEVNULL)
        self.assertNotIn("shell", seen)
        self.assertEqual(seen["argv"], ["x", "y"])


if __name__ == "__main__":
    unittest.main()
