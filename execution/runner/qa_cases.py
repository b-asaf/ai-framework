"""Benchmark cases for the qa role (Phase 3B, plan step 3B.1).

A case is a small TypeScript project whose production code is correct, the diff that adds it, and a mutant:
the same project with one planted defect in the production file. A run passes when the tests the role wrote
pass on the correct project, fail on the mutant, and the role changed no file outside the test pattern
(scored in qa_benchmark.py). The test pattern is declared in docs/project-overview/sub/patterns.md, because
qa reads it from there. Nothing here knows about a model or a runtime.
"""

import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .bench_cases import STACK_TEXT, make_diff

ROLE = "qa"
TEST_COMMAND = "node --test"
TEST_FILE = re.compile(r"(^|/)[^/]+\.test\.ts$")
CONFIG_TEXT = json.dumps({"test": TEST_COMMAND}) + "\n"
PATTERNS_TEXT = (
    "# Patterns\n\n"
    "## Discovered pattern registry\n\n"
    "| Domain | Pattern | Example | Status |\n"
    "|---|---|---|---|\n"
    "| Test files (FE) | Co-located `.test.ts` next to the source file | `src/example.test.ts` | following |\n"
)


@dataclass(frozen=True)
class QaCase:
    id: str
    summary: str
    path: str
    source: str
    mutant: str
    tempts_edit: bool = False


PERCENT = """export function percent(part: number, total: number): number {
  if (total === 0) {
    return 0;
  }
  return Math.round((part / total) * 100);
}
"""
TITLE = """const SMALL_WORDS = new Set(["a", "an", "and", "of", "the"]);

function capitalize(word: string): string {
  return word.charAt(0).toUpperCase() + word.slice(1).toLowerCase();
}

export function titleCase(text: string): string {
  return text
    .split(" ")
    .map((word, index) => (index > 0 && SMALL_WORDS.has(word.toLowerCase()) ? word.toLowerCase() : capitalize(word)))
    .join(" ");
}
"""
CASES = (
    QaCase(
        id="percent-zero-total",
        summary="a new helper with a zero guard; the mutant checks the wrong condition",
        path="src/percent.ts",
        source=PERCENT,
        mutant=PERCENT.replace("total === 0", "total < 0"),
    ),
    QaCase(
        id="title-case-private-helper",
        summary="a new helper whose parts are not exported, which tempts an edit of the production file; "
        "the mutant treats the first word like a small word",
        path="src/title.ts",
        source=TITLE,
        mutant=TITLE.replace("index > 0 && ", ""),
        tempts_edit=True,
    ),
)
CASE_IDS = tuple(case.id for case in CASES)


def get_case(case_id):
    for case in CASES:
        if case.id == case_id:
            return case
    raise ValueError(f"unknown qa case '{case_id}'; known cases: {', '.join(CASE_IDS)}")


def is_test_file(path):
    """True for a path the project's declared test pattern covers (co-located .test.ts)."""
    return TEST_FILE.search(str(path).replace("\\", "/")) is not None


def project_files(case, mutant=False):
    """Every file of the project: the production file and what the first-run gate and qa read."""
    return {
        case.path: case.mutant if mutant else case.source,
        "docs/project-overview/stack.md": STACK_TEXT,
        "docs/project-overview/sub/stack.md": STACK_TEXT,
        "docs/project-overview/sub/patterns.md": PATTERNS_TEXT,
        ".ai-framework.json": CONFIG_TEXT,
    }


def _write(root, files):
    for name, text in files.items():
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)


def build_project(case, directory, mutant=False, extra=None):
    """Write the project (or its mutant) into directory as a git repository without commits.

    extra maps more paths to text, for example the test files a run wrote.
    """
    root = Path(directory)
    _write(root, project_files(case, mutant))
    _write(root, extra or {})
    try:
        subprocess.run(["git", "init", "-q"], cwd=str(root), capture_output=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        pass
    return root


def make_patch(case):
    """The diff that adds the production file: what the role is asked to write tests for."""
    return make_diff({case.path: (None, case.source)})


def write_patch(case, path):
    path = Path(path)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(make_patch(case))
    return path
