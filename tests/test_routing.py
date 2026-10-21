import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tools"))

import validate_framework  # noqa: E402
from lib.policy import load_policy  # noqa: E402
from lib.routing import (  # noqa: E402
    ProfileError,
    load_profile,
    profile_models,
    render_routing,
    routing_text,
)

PROFILE = REPO / "execution" / "profiles" / "default.json"
ROUTING = REPO / "execution" / "routing.json"
POLICY = REPO / "execution" / "policy.json"
GENERATOR = REPO / "tools" / "generate_routing.py"


def make_policy(*models):
    entry = {"family": "x", "status": "approved", "evaluation": None}
    return {"models": {m: dict(entry) for m in models}, "constraints": {"independence": []}}


def make_profile(**agents):
    return {"version": 1, "agents": {name: {"model": model} for name, model in agents.items()}}


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


class RenderRouting(unittest.TestCase):
    def test_output_has_one_sorted_entry_per_agent(self):
        routing = render_routing(make_profile(b="m/two", a="m/one"), make_policy("m/one", "m/two"))
        self.assertEqual(
            routing,
            {"$schema": "https://opencode.ai/config.json", "agent": {"a": {"model": "m/one"}, "b": {"model": "m/two"}}},
        )
        self.assertEqual(list(routing["agent"]), ["a", "b"])

    def test_model_missing_from_policy_is_refused_naming_agent_and_model(self):
        with self.assertRaises(ProfileError) as ctx:
            render_routing(make_profile(a="m/nope"), make_policy("m/one"))
        self.assertIn("a (m/nope)", str(ctx.exception))

    def test_schema_line_comes_first_so_opencode_does_not_rewrite_the_file(self):
        text = routing_text(render_routing(make_profile(a="m/one"), make_policy("m/one")))
        self.assertEqual(text.splitlines()[1], '  "$schema": "https://opencode.ai/config.json",')

    def test_text_is_stable_and_ends_with_newline(self):
        routing = render_routing(make_profile(a="m/one"), make_policy("m/one"))
        self.assertEqual(routing_text(routing), routing_text(json.loads(routing_text(routing))))
        self.assertTrue(routing_text(routing).endswith("\n"))
        self.assertNotIn("\r", routing_text(routing))


class LoadProfile(unittest.TestCase):
    def load(self, data):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "default.json"
            if isinstance(data, str):
                path.write_text(data, encoding="utf-8")
            else:
                write_json(path, data)
            return load_profile(path)

    def test_missing_file_fails(self):
        with self.assertRaises(ProfileError):
            load_profile(Path(tempfile.gettempdir()) / "no-such-dir" / "default.json")

    def test_invalid_json_fails(self):
        with self.assertRaises(ProfileError):
            self.load("{not json")

    def test_empty_agents_fails(self):
        with self.assertRaises(ProfileError):
            self.load({"version": 1, "agents": {}})

    def test_agent_without_model_fails_naming_agent(self):
        with self.assertRaises(ProfileError) as ctx:
            self.load({"version": 1, "agents": {"qa": {}}})
        self.assertIn("qa", str(ctx.exception))

    def test_capability_is_optional_documentation(self):
        profile = self.load({"version": 1, "agents": {"qa": {"model": "m/one", "capability": "testing"}}})
        self.assertEqual(profile_models(profile), {"qa": "m/one"})

    def test_capability_must_be_a_string(self):
        with self.assertRaises(ProfileError):
            self.load({"version": 1, "agents": {"qa": {"model": "m/one", "capability": 3}}})


class RealRepo(unittest.TestCase):
    def test_committed_routing_equals_the_rendered_profile(self):
        expected = routing_text(render_routing(load_profile(PROFILE), load_policy(POLICY)))
        self.assertEqual(ROUTING.read_bytes().decode("utf-8"), expected)

    def test_no_agent_file_has_a_model_line(self):
        agents = validate_framework.discover_agents(REPO / "agents")
        self.assertEqual([agent.name for agent in agents if agent.model], [])


class Cli(unittest.TestCase):
    def run_generator(self, root, *extra):
        return subprocess.run(
            [sys.executable, str(GENERATOR), "--repo", str(root), *extra],
            capture_output=True, text=True,
        )

    def make_repo(self, tmp, profile):
        root = Path(tmp)
        write_json(root / "execution" / "policy.json", make_policy("m/one", "m/two"))
        write_json(root / "execution" / "profiles" / "default.json", profile)
        return root

    def test_write_then_check_then_drift(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.make_repo(tmp, make_profile(a="m/one", b="m/two"))
            self.assertEqual(self.run_generator(root).returncode, 0)
            first = (root / "execution" / "routing.json").read_bytes()
            self.assertEqual(self.run_generator(root).returncode, 0)
            self.assertEqual((root / "execution" / "routing.json").read_bytes(), first)
            self.assertEqual(self.run_generator(root, "--check").returncode, 0)
            (root / "execution" / "routing.json").write_text("{}\n", encoding="utf-8")
            self.assertEqual(self.run_generator(root, "--check").returncode, 1)

    def test_check_without_a_routing_file_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.make_repo(tmp, make_profile(a="m/one"))
            self.assertEqual(self.run_generator(root, "--check").returncode, 1)

    def test_unknown_model_fails_and_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.make_repo(tmp, make_profile(a="m/nope"))
            result = self.run_generator(root)
            self.assertEqual(result.returncode, 1)
            self.assertIn("m/nope", result.stdout)
            self.assertFalse((root / "execution" / "routing.json").exists())


if __name__ == "__main__":
    unittest.main()
