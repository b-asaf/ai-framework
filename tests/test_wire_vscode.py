"""Tests for wire_vscode in setup.py: it must never damage the developer's VS Code settings.json."""
import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tools"))
sys.path.insert(0, str(REPO))

import setup as framework_setup  # noqa: E402

CODE_KEY = "github.copilot.chat.codeGeneration.instructions"
COMMIT_KEY = "github.copilot.chat.commitMessageGeneration.instructions"


class WireVscodeCase(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name).resolve()
        self.fw = self.tmp / "framework"
        self.settings = self.tmp / "Code" / "User" / "settings.json"
        self.bak = self.settings.with_name("settings.json.ai-framework.bak")
        for patcher in (
            mock.patch.object(framework_setup, "REPO", self.fw),
            mock.patch.object(framework_setup, "INSTRUCTIONS", self.fw / "instructions"),
            mock.patch.object(framework_setup, "VSCODE_SETTINGS", self.settings),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)

    def wire(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            framework_setup.wire_vscode({"copilot_vscode": True})
        return out.getvalue()

    def write(self, text):
        self.settings.parent.mkdir(parents=True, exist_ok=True)
        self.settings.write_text(text, encoding="utf-8", newline="\n")

    def load(self):
        return json.loads(self.settings.read_text(encoding="utf-8"))

    def files(self, key):
        return [entry["file"] for entry in self.load()[key]]

    def test_creates_the_file_with_both_settings(self):
        self.wire()
        self.assertEqual([Path(f).name for f in self.files(CODE_KEY)], ["AGENTS.md", "COPILOT.md"])
        self.assertEqual([Path(f).name for f in self.files(COMMIT_KEY)], ["GIT_COMMIT.md"])

    def test_not_detected_writes_nothing(self):
        framework_setup.wire_vscode({"copilot_vscode": False})
        self.assertFalse(self.settings.exists())

    def test_empty_file_is_treated_as_empty_settings(self):
        self.write("")
        self.wire()
        self.assertIn(CODE_KEY, self.load())

    def test_keeps_other_settings_and_saves_a_backup(self):
        original = '{\n  "search.exclude": {"**/*.js": true, "**/*.ts": true},\n  "editor.tabSize": 2\n}\n'
        self.write(original)
        self.wire()
        data = self.load()
        self.assertEqual(data["search.exclude"], {"**/*.js": True, "**/*.ts": True})
        self.assertEqual(data["editor.tabSize"], 2)
        self.assertEqual(self.bak.read_text(encoding="utf-8"), original)

    def test_backup_is_kept_from_the_first_change(self):
        original = '{"editor.tabSize": 2}\n'
        self.write(original)
        self.wire()
        data = self.load()
        data[CODE_KEY] = []
        self.write(json.dumps(data))
        self.wire()
        self.assertEqual(self.bak.read_text(encoding="utf-8"), original)

    def test_comments_leave_the_file_untouched(self):
        original = '{\n  // my note\n  "http.proxy": "http://proxy:8080",\n  "editor.tabSize": 2\n}\n'
        self.write(original)
        out = self.wire()
        self.assertEqual(self.settings.read_text(encoding="utf-8"), original)
        self.assertFalse(self.bak.exists())
        self.assertIn(CODE_KEY, out)

    def test_second_run_changes_nothing(self):
        self.write('{"editor.tabSize": 2}\n')
        self.wire()
        first = self.settings.read_bytes()
        out = self.wire()
        self.assertEqual(self.settings.read_bytes(), first)
        self.assertIn("already configured", out)

    def test_drops_the_old_vscode_md_entry_and_keeps_own_entries(self):
        old = {"file": str(self.fw / "instructions" / "VSCODE.md")}
        mine = {"file": "C:/mine/own.md"}
        self.write(json.dumps({CODE_KEY: [old, mine]}))
        self.wire()
        files = self.files(CODE_KEY)
        self.assertIn("C:/mine/own.md", files)
        self.assertFalse([f for f in files if f.endswith("VSCODE.md")])
        self.assertEqual(files[-1], str(self.fw / "instructions" / "COPILOT.md"))

    def test_sibling_folder_with_the_same_prefix_is_kept(self):
        sibling = str(self.tmp / "framework-notes" / "mine.md")
        self.write(json.dumps({CODE_KEY: [{"file": sibling}]}))
        self.wire()
        self.assertIn(sibling, self.files(CODE_KEY))

    def test_framework_entry_with_forward_slashes_is_replaced_not_duplicated(self):
        slashed = (self.fw / "instructions" / "COPILOT.md").as_posix()
        self.write(json.dumps({CODE_KEY: [{"file": slashed}]}))
        self.wire()
        self.assertEqual([Path(f).name for f in self.files(CODE_KEY)], ["AGENTS.md", "COPILOT.md"])


class InstructionFilesCase(unittest.TestCase):
    def test_vscode_md_is_merged_into_copilot_md(self):
        self.assertFalse((REPO / "instructions" / "VSCODE.md").exists())

    def test_copilot_header_does_not_claim_a_project_file(self):
        text = (REPO / "instructions" / "COPILOT.md").read_text(encoding="utf-8")
        self.assertNotIn("copilot-instructions.md", text)


if __name__ == "__main__":
    unittest.main()
