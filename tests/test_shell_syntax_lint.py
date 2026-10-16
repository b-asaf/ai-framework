import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tools"))

import validate_framework  # noqa: E402


def write(root, rel, text):
    path = Path(root) / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


class ShellSyntaxLintTest(unittest.TestCase):
    def lint(self, files):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            for rel, text in files.items():
                write(tmp, rel, text)
            return validate_framework.lint_shell_syntax(Path(tmp))

    def test_clean_tree_has_no_issues(self):
        issues = self.lint({
            "agents/a.md": 'python "$HOME/.config/opencode/scripts/x.py"\n',
            "AGENTS.md": "plain text\n",
        })
        self.assertEqual(issues, [])

    def test_env_variable_in_agent_is_reported_with_line(self):
        issues = self.lint({"agents/a.md": 'ok\npython "$env:USERPROFILE\\x.py"\n'})
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].check, "shell-syntax")
        self.assertEqual(issues[0].file, "agents/a.md")
        self.assertIn("line 2", issues[0].message)

    def test_agents_md_and_removed_script_are_reported(self):
        issues = self.lint({
            "AGENTS.md": "call git-context.ps1 and $Env:HOME\n",
            "skills/s/SKILL.md": "use $env:TOKEN\n",
        })
        files = sorted(i.file for i in issues)
        self.assertEqual(files, ["AGENTS.md", "AGENTS.md", "skills/s/SKILL.md"])

    def test_jscpd_report_output_in_a_skill_is_reported(self):
        issues = self.lint({"skills/s/SKILL.md": "jscpd --reporters json --output .jscpd-report src/\n"})
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].check, "shell-syntax")
        self.assertIn("static-analysis.py", issues[0].message)

    def test_exempt_paths_are_not_scanned(self):
        issues = self.lint({
            "tests/t.py": "$env:USERPROFILE git-context.ps1\n",
            "tools/v.py": "$env:USERPROFILE\n",
            "scripts/s.py": "git-context.ps1\n",
            "docs/decisions/DEC-012.md": "$env:USERPROFILE\n",
            "CHANGELOG.md": "$env:USERPROFILE\n",
        })
        self.assertEqual(issues, [])


if __name__ == "__main__":
    unittest.main()
