import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tools"))
sys.path.insert(0, str(REPO))

import setup as framework_setup  # noqa: E402
import validate_framework  # noqa: E402
from lib.opencode_config import agent_model_problems  # noqa: E402

DETECTED = {
    "opencode": True,
    "claude": False,
    "codex": False,
    "gemini": False,
    "copilot_intellij": False,
    "copilot_vscode": False,
}


def agent(name, model=None, tasks=None):
    return validate_framework.Agent(
        path=Path(f"agents/{name}.md"),
        mode="subagent",
        model=model,
        permission={},
        task_permissions=tasks or {},
    )


def make_repo(tmp, profile_agents):
    root = Path(tmp)
    path = root / "execution" / "profiles" / "default.json"
    path.parent.mkdir(parents=True)
    data = {"version": 1, "agents": {n: {"model": m} for n, m in profile_agents.items()}}
    path.write_text(json.dumps(data), encoding="utf-8")
    return root


class SetupLinks(unittest.TestCase):
    def rows(self, **overrides):
        det = dict(DETECTED, **overrides)
        return {link.name: (target, kind) for link, target, kind in framework_setup.build_links(det)}

    def test_routing_is_linked_as_config_json(self):
        target, kind = self.rows()["config.json"]
        self.assertEqual(target, REPO / "execution" / "routing.json")
        self.assertEqual(kind, "file")
        self.assertTrue(target.is_file())

    def test_opencode_json_link_is_unchanged(self):
        self.assertEqual(self.rows()["opencode.json"], (REPO / "opencode.json", "file"))

    def test_no_config_json_without_opencode(self):
        self.assertNotIn("config.json", self.rows(opencode=False))


class RoutedAgents(unittest.TestCase):
    def test_profile_model_fills_a_missing_model_line(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_repo(tmp, {"a": "m/one"})
            routed = validate_framework.routed_agents(root, [agent("a")])
        self.assertEqual(routed[0].model, "m/one")

    def test_a_model_line_wins_like_in_opencode(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_repo(tmp, {"a": "m/one"})
            routed = validate_framework.routed_agents(root, [agent("a", "m/two")])
        self.assertEqual(routed[0].model, "m/two")

    def test_the_original_agents_are_not_changed(self):
        original = agent("a")
        with tempfile.TemporaryDirectory() as tmp:
            validate_framework.routed_agents(make_repo(tmp, {"a": "m/one"}), [original])
        self.assertIsNone(original.model)

    def test_unreadable_profile_returns_the_agents_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            agents = [agent("a")]
            self.assertEqual(validate_framework.routed_agents(Path(tmp), agents), agents)

    def test_a_routed_agent_passes_the_model_exists_check(self):
        catalog = {"m/one": "x"}
        with tempfile.TemporaryDirectory() as tmp:
            root = make_repo(tmp, {"a": "m/one"})
            routed = validate_framework.routed_agents(root, [agent("a")])
        self.assertEqual(validate_framework.validate_model_exists(routed[0], catalog), [])
        self.assertEqual(len(validate_framework.validate_model_exists(agent("a"), catalog)), 1)

    def test_cross_family_edges_use_the_profile_models(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_repo(tmp, {"a": "m/one", "b": "m/two"})
            routed = validate_framework.routed_agents(root, [agent("a", tasks={"b": "allow"}), agent("b")])
        edges = validate_framework.find_cross_family_edges(routed, {"m/one": "x", "m/two": "y"})
        self.assertEqual(len(edges), 1)


class AgentModelInOpencodeJson(unittest.TestCase):
    def test_agent_model_is_flagged_naming_the_agent(self):
        problems = agent_model_problems({"agent": {"qa": {"model": "m/one"}}})
        self.assertEqual(len(problems), 1)
        self.assertIn("agent.qa.model", problems[0])

    def test_agent_without_a_model_passes(self):
        self.assertEqual(agent_model_problems({"agent": {"qa": {"permission": {}}}}), [])

    def test_no_agent_section_or_a_wrong_shape_passes(self):
        self.assertEqual(agent_model_problems({}), [])
        self.assertEqual(agent_model_problems({"agent": []}), [])

    def test_lint_reports_it_for_a_repo(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "opencode.json").write_text(
                json.dumps({"agent": {"qa": {"model": "m/one"}}}), encoding="utf-8"
            )
            issues = validate_framework.lint_opencode_config(Path(tmp))
        self.assertIn("agent.qa.model", " | ".join(str(issue) for issue in issues))


if __name__ == "__main__":
    unittest.main()
