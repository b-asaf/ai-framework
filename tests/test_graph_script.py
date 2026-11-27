import importlib.util
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parent.parent
SCRIPT = REPO / "scripts" / "graph.py"
SPEC = importlib.util.spec_from_file_location("graph_script", SCRIPT)
graph = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(graph)
REAL_GRAPHIFY = graph.graphify


def git(folder, *args):
    return subprocess.run(
        ["git", "-C", str(folder), "-c", "user.name=t", "-c", "user.email=t@example.com", *args],
        check=True, capture_output=True, text=True, stdin=subprocess.DEVNULL,
    )


class FakeGraphify:
    """Stands in for the graphify command: records the calls and writes the graph where GRAPHIFY_OUT points."""

    def __init__(self):
        self.calls = []
        self.returncode = 0

    def __call__(self, args, repo, timeout, extra_env=None):
        env = dict(extra_env or {})
        self.calls.append((list(args), Path(repo), env))
        if self.returncode == 0 and args[0] in ("extract", "update") and "GRAPHIFY_OUT" in env:
            Path(env["GRAPHIFY_OUT"]).mkdir(parents=True, exist_ok=True)
            (Path(env["GRAPHIFY_OUT"]) / "graph.json").write_text("{}", encoding="utf-8")
        return subprocess.CompletedProcess(args, self.returncode, "OUT\n", "")


class GraphScript(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(tmp.cleanup)
        self.repo = Path(tmp.name).resolve()
        git(self.repo, "init", "-q", "--template=", "-b", "main")
        self.fake = FakeGraphify()
        patcher = mock.patch.object(graph, "graphify", self.fake)
        patcher.start()
        self.addCleanup(patcher.stop)

    def run_script(self, *argv):
        out = StringIO()
        with redirect_stdout(out):
            code = graph.main(["--repo", str(self.repo), *argv])
        return code, out.getvalue()

    def write_config(self, text):
        (self.repo / ".ai-framework.json").write_text(text, encoding="utf-8", newline="\n")

    def test_build_puts_the_graph_in_the_generated_folder(self):
        code, out = self.run_script("build")
        self.assertEqual(code, 0, out)
        self.assertIn("STATUS: OK", out)
        self.assertIn(".ai-framework/graphify/graphify-out/graph.json", out)
        args, cwd, env = self.fake.calls[0]
        self.assertEqual(args, ["extract", ".", "--code-only"])
        self.assertEqual(cwd.resolve(), self.repo)
        self.assertTrue(Path(env["GRAPHIFY_OUT"]).as_posix().endswith(".ai-framework/graphify/graphify-out"))

    def test_the_folder_ignores_everything_in_it_so_git_add_takes_nothing(self):
        self.run_script("build")
        ignore = self.repo / ".ai-framework" / "graphify" / ".gitignore"
        self.assertEqual(ignore.read_text(encoding="utf-8"), "*\n")
        (self.repo / "a.txt").write_text("a\n", encoding="utf-8", newline="\n")
        git(self.repo, "add", ".")
        self.assertEqual(git(self.repo, "diff", "--cached", "--name-only").stdout.split(), ["a.txt"])

    def test_update_without_a_graph_builds_it(self):
        code, _ = self.run_script("update")
        self.assertEqual(code, 0)
        self.assertEqual(self.fake.calls[0][0][0], "extract")

    def test_update_with_a_graph_runs_the_update(self):
        self.run_script("build")
        code, out = self.run_script("update")
        self.assertEqual(code, 0, out)
        self.assertEqual(self.fake.calls[1][0], ["update", "."])
        self.assertIn("GRAPHIFY_OUT", self.fake.calls[1][2])

    def test_generated_dir_is_respected(self):
        self.write_config('{"generatedDir": "gen/out"}\n')
        code, out = self.run_script("build")
        self.assertEqual(code, 0, out)
        self.assertIn("gen/out/graphify/graphify-out/graph.json", out)

    def test_a_bad_generated_dir_is_an_error(self):
        self.write_config('{"generatedDir": "../outside"}\n')
        code, out = self.run_script("build")
        self.assertEqual(code, 2)
        self.assertIn("STATUS: ERROR", out)
        self.assertIn("REASON:", out)

    def test_read_commands_need_a_graph(self):
        code, out = self.run_script("query", "anything")
        self.assertEqual(code, 2)
        self.assertIn("no graph yet", out)
        self.assertEqual(self.fake.calls, [])

    def test_read_commands_pass_the_graph_file_to_graphify(self):
        self.run_script("build")
        for words in (("query", "how"), ("path", "A", "B"), ("explain", "X")):
            with self.subTest(command=words[0]):
                code, out = self.run_script(*words)
                self.assertEqual(code, 0)
                self.assertEqual(out, "OUT\n")
                args = self.fake.calls[-1][0]
                self.assertEqual(args[:-2], list(words))
                self.assertEqual(args[-2], "--graph")
                self.assertTrue(Path(args[-1]).as_posix().endswith("graphify-out/graph.json"))

    def test_a_failing_graphify_is_an_error(self):
        self.fake.returncode = 1
        code, out = self.run_script("build")
        self.assertEqual(code, 2)
        self.assertIn("failed", out)

    def test_outside_a_repository_is_an_error(self):
        not_a_repo = subprocess.CompletedProcess([], 128, "", "fatal")
        with mock.patch.object(graph, "_run", return_value=not_a_repo):
            code, out = self.run_script("build")
        self.assertEqual(code, 2)
        self.assertIn("not inside a git repository", out)

    def test_a_missing_graphify_command_is_an_error(self):
        with mock.patch.object(graph.shutil, "which", return_value=None):
            with self.assertRaises(graph.GraphError):
                REAL_GRAPHIFY(["extract"], self.repo, 1)

    def test_the_script_never_runs_graphifys_installers(self):
        text = SCRIPT.read_text(encoding="utf-8")
        for word in ('"install"', '"uninstall"', '"hook"'):
            with self.subTest(word=word):
                self.assertNotIn(word, text)


if __name__ == "__main__":
    unittest.main()
