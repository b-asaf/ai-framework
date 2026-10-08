import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tools"))

import validate_agents  # noqa: E402
from lib.opencode_models import (  # noqa: E402
    LiveModelError,
    fetch_live_models,
    find_unknown_models,
    parse_models,
)

SAMPLE = """github-copilot/claude-sonnet-5
github-copilot/gpt-5.6-terra

opencode/big-pickle
not a model line
"""
LIVE = {"github-copilot/gpt-5.6-terra", "github-copilot/claude-sonnet-5"}
GHOST = REPO / "tests" / "fixtures" / "unknown-model" / "agents" / "ghost-agent.md"
GOOD = REPO / "tests" / "fixtures" / "good-escape" / "agents" / "good.md"


def fake_runner(stdout="", returncode=0, stderr=""):
    def runner(command, **kwargs):
        return subprocess.CompletedProcess(command, returncode, stdout=stdout, stderr=stderr)
    return runner


def found(name):
    return "/fake/opencode"


class LiveModelParsing(unittest.TestCase):
    def test_parse_keeps_provider_model_lines(self):
        self.assertEqual(
            parse_models(SAMPLE),
            {
                "github-copilot/claude-sonnet-5",
                "github-copilot/gpt-5.6-terra",
                "opencode/big-pickle",
            },
        )

    def test_find_unknown_models(self):
        agents = {"a": "github-copilot/gpt-5.6-terra", "b": "github-copilot/nope"}
        self.assertEqual(find_unknown_models(agents, LIVE), [("b", "github-copilot/nope")])


class LiveModelFetch(unittest.TestCase):
    def test_fetch_returns_ids(self):
        models = fetch_live_models(runner=fake_runner(SAMPLE), which=found)
        self.assertIn("github-copilot/gpt-5.6-terra", models)

    def test_missing_opencode_fails_closed(self):
        with self.assertRaises(LiveModelError) as caught:
            fetch_live_models(runner=fake_runner(SAMPLE), which=lambda name: None)
        self.assertIn("not found", str(caught.exception))

    def test_nonzero_exit_fails_closed(self):
        with self.assertRaises(LiveModelError) as caught:
            fetch_live_models(runner=fake_runner("", 1, "boom"), which=found)
        self.assertIn("boom", str(caught.exception))

    def test_empty_list_fails_closed(self):
        with self.assertRaises(LiveModelError):
            fetch_live_models(runner=fake_runner("\n"), which=found)


class ValidatorLiveCheck(unittest.TestCase):
    def test_unknown_model_names_agent_and_id(self):
        agent = validate_agents.load_agent(GHOST)
        with mock.patch("validate_agents.fetch_live_models", return_value=LIVE):
            issues = validate_agents.check_live_models([agent])
        self.assertEqual(len(issues), 1)
        text = str(issues[0])
        self.assertIn("ghost-agent", text)
        self.assertIn("github-copilot/nope", text)

    def test_known_model_passes(self):
        agent = validate_agents.load_agent(GOOD)
        with mock.patch("validate_agents.fetch_live_models", return_value=LIVE):
            self.assertEqual(validate_agents.check_live_models([agent]), [])

    def test_unreadable_list_is_reported(self):
        agent = validate_agents.load_agent(GOOD)
        error = LiveModelError("cannot read the list")
        with mock.patch("validate_agents.fetch_live_models", side_effect=error):
            issues = validate_agents.check_live_models([agent])
        self.assertEqual(len(issues), 1)
        self.assertIn("cannot read the list", str(issues[0]))


if __name__ == "__main__":
    unittest.main()
