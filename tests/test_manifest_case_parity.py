"""Manifest matching must agree between the pre-push checks and scripts/quick-lane-check.py.

The script runs inside projects where the framework package is not importable, so it keeps
its own pattern list. These tests run the same paths through the dependency check, the
quick-lane check and the script, so a list or a case rule that drifts apart fails here.
"""
import importlib.util
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from execution.verification.checks import dependency_change, quick_lane  # noqa: E402


def _load_script():
    spec = importlib.util.spec_from_file_location(
        "quick_lane_check_script", REPO / "scripts" / "quick-lane-check.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


SCRIPT = _load_script()

MANIFESTS = [
    "package.json", "Package.json", "PACKAGE-LOCK.JSON", "yarn.lock", "Yarn.Lock",
    "pnpm-lock.yaml", "pom.xml", "POM.XML", "build.gradle", "Build.Gradle",
    "build.gradle.kts", "Build.Gradle.KTS", "requirements.txt", "requirements-dev.txt",
    "Requirements-Dev.TXT", "pyproject.toml", "PyProject.toml", "poetry.lock",
    "Pipfile", "pipfile", "Pipfile.lock", "PIPFILE.LOCK",
    "services/api/Package.json", "a/b/POM.xml",
]
NOT_MANIFESTS = [
    "README.md", "requirements.md", "my-package.json", "package.jsonx",
    "src/package/index.js", "docs/pom.xml.md", "gradle.properties",
]


def by_dependency_check(path):
    return bool(dependency_change.find_violations([path], []))


def by_quick_lane_check(path):
    measurement = {"sha": "x", "files": 1, "lines": 1, "paths": [path]}
    return bool(
        quick_lane.find_violations([measurement], quick_lane.RESTRICTED_PATTERNS, 3, 60)
    )


def by_script(path):
    return bool(SCRIPT.restricted([path]))


class ManifestMatchingParity(unittest.TestCase):
    def test_pattern_lists_agree(self):
        script = sorted(pattern.lower() for pattern in SCRIPT.RESTRICTED_PATTERNS)
        check = sorted(pattern.lower() for pattern in quick_lane.RESTRICTED_PATTERNS)
        self.assertEqual(script, check)

    def test_manifests_match_in_every_case_in_all_three_places(self):
        for path in MANIFESTS:
            for predicate in (by_dependency_check, by_quick_lane_check, by_script):
                with self.subTest(path=path, predicate=predicate.__name__):
                    self.assertTrue(predicate(path))

    def test_ai_framework_json_is_restricted_for_the_lane_but_is_not_a_manifest(self):
        for path in (".ai-framework.json", "sub/.AI-Framework.JSON"):
            with self.subTest(path=path):
                self.assertFalse(by_dependency_check(path))
                self.assertTrue(by_quick_lane_check(path))
                self.assertTrue(by_script(path))

    def test_other_files_match_nowhere(self):
        for path in NOT_MANIFESTS:
            for predicate in (by_dependency_check, by_quick_lane_check, by_script):
                with self.subTest(path=path, predicate=predicate.__name__):
                    self.assertFalse(predicate(path))

    def test_the_violation_reports_the_path_as_pushed(self):
        violations = dependency_change.find_violations(["Services/Package.json"], [])
        self.assertEqual(violations[0]["manifests"], ["Services/Package.json"])


if __name__ == "__main__":
    unittest.main()
