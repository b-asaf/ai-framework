import re
import subprocess
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
FOLDER_LINE = re.compile(r"^([A-Za-z0-9_.-]+)/")


def tracked_folders():
    out = subprocess.run(
        ["git", "ls-files"], cwd=str(REPO), capture_output=True, text=True, encoding="utf-8", check=True
    ).stdout
    return {line.split("/")[0] for line in out.splitlines() if "/" in line}


def readme_lines():
    return (REPO / "README.md").read_text(encoding="utf-8").splitlines()


def structure_block():
    lines = readme_lines()
    start = lines.index("## Repo structure")
    first = next(i for i in range(start, len(lines)) if lines[i] == "```")
    last = next(i for i in range(first + 1, len(lines)) if lines[i] == "```")
    return lines[first + 1:last]


def named_folders():
    matches = (FOLDER_LINE.match(line) for line in structure_block())
    return {match.group(1) for match in matches if match}


class ReadmeFolderMap(unittest.TestCase):
    def test_every_tracked_top_level_folder_has_a_line(self):
        missing = tracked_folders() - named_folders()
        self.assertEqual(missing, set(), f"README 'Repo structure' has no line for: {sorted(missing)}")

    def test_every_folder_the_block_names_is_tracked(self):
        stale = named_folders() - tracked_folders()
        self.assertEqual(stale, set(), f"README 'Repo structure' names folders that are not tracked: {sorted(stale)}")

    def test_the_scripts_and_tools_split_is_stated(self):
        text = "\n".join(readme_lines())
        self.assertIn("`scripts/` and `tools/` are different on purpose", text)


if __name__ == "__main__":
    unittest.main()
