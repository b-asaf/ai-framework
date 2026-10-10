import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tools"))

from lib.model_strings import find_model_ids, scan_folders  # noqa: E402

CATALOG = "docs/decisions/MODEL-ASSIGNMENT-MATRIX.md"


class FindModelIds(unittest.TestCase):
    def matches(self, text):
        return [match for _, match in find_model_ids(text)]

    def test_provider_model_ids_are_found(self):
        self.assertEqual(
            self.matches('"model": "github-copilot/gpt-5.6-terra"'),
            ["github-copilot/gpt-5.6-terra"],
        )
        self.assertEqual(self.matches("use anthropic/claude-opus-4 here"), ["anthropic/claude-opus-4"])
        self.assertEqual(self.matches("openai/gpt-4o"), ["openai/gpt-4o"])

    def test_bare_ids_are_found(self):
        for text, expected in (
            ("claude-sonnet-5", "claude-sonnet-5"),
            ("gpt-5.3-codex", "gpt-5.3-codex"),
            ("gemini-2.5-pro", "gemini-2.5-pro"),
            ("gpt4o", "gpt4o"),
            ("codex-mini-latest", "codex-mini-latest"),
            ("o3-mini", "o3-mini"),
            ("o1", "o1"),
        ):
            with self.subTest(text=text):
                self.assertEqual(self.matches("model is " + text + " today"), [expected])

    def test_line_numbers_are_reported(self):
        found = find_model_ids("line one\nthe id claude-opus-5.5 is here\n")
        self.assertEqual(found, [(2, "claude-opus-5.5")])

    def test_prose_and_paths_are_ignored(self):
        for text in (
            "GPT models may be used for review.",
            "Claude and Gemini are model families.",
            "Codex models belong to the gpt family.",
            "Claude Code is the CLI, and gpt-style prompts are fine.",
            "files live in .opencode/agents/reviewer.md",
            "the opencode runtime runs agents",
            "version 1.3 of the schema, step o2 is unrelated",
        ):
            with self.subTest(text=text):
                self.assertEqual(find_model_ids(text), [])


class ScanFolders(unittest.TestCase):
    def write(self, root, relative, text):
        path = Path(root) / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def test_ids_in_checked_folders_are_reported_with_path_and_line(self):
        with tempfile.TemporaryDirectory() as root:
            self.write(root, "roles/reviewer.json", '{\n  "model": "claude-sonnet-5"\n}\n')
            self.write(root, "verification/checks/build.py", "# runs the build\n")
            self.write(root, "execution/schemas/run.schema.json", '{"title": "gpt-5.4"}')
            found = scan_folders(root)
            self.assertEqual(
                found,
                [
                    ("roles/reviewer.json", 2, "claude-sonnet-5"),
                    ("execution/schemas/run.schema.json", 1, "gpt-5.4"),
                ],
            )

    def test_policy_and_profiles_may_name_models(self):
        with tempfile.TemporaryDirectory() as root:
            self.write(root, "execution/policy.json", '{"github-copilot/gpt-5.6-terra": {}}')
            self.write(root, "execution/profiles/default.json", '{"reviewer": "claude-sonnet-5"}')
            self.assertEqual(scan_folders(root), [])

    def test_missing_folders_are_skipped(self):
        with tempfile.TemporaryDirectory() as root:
            self.assertEqual(scan_folders(root), [])


class ValidatorFixtures(unittest.TestCase):
    def run_validator(self, fixture):
        env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
        return subprocess.run(
            [sys.executable, str(REPO / "tools" / "validate_framework.py"),
             "tests/fixtures/" + fixture, CATALOG],
            cwd=REPO, env=env, capture_output=True,
            encoding="utf-8", errors="replace",
        )

    def test_role_with_a_model_id_fails(self):
        result = self.run_validator("model-string-bad")
        output = result.stdout + result.stderr
        self.assertEqual(result.returncode, 1, output)
        self.assertIn("[model-string] roles/reviewer.json:4", output)
        self.assertIn("github-copilot/gpt-5.6-terra", output)

    def test_role_with_a_prose_mention_passes_this_check(self):
        result = self.run_validator("model-string-ok")
        self.assertNotIn("[model-string]", result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
