import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tools"))

import validate_framework  # noqa: E402
from lib.opencode_resolved import (  # noqa: E402
    ResolvedModelError,
    fetch_resolved_model,
    find_opencode,
    parse_resolved_model,
)
from lib.routing import (  # noqa: E402
    check_coverage,
    check_frontmatter_conflicts,
    check_routing_text,
    render_routing,
    routing_text,
)

SAMPLE = (
    '{\n  "name": "qa",\n  "model": {\n    "providerID": "github-copilot",\n'
    '    "modelID": "gpt-5.4-mini"\n  },\n  "permission": []\n}\n'
)
EDGE = {"producer": "architect", "validator": "plan-reviewer", "rule": "different-family"}


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def agent(name, model=None):
    return validate_framework.Agent(
        path=Path(f"agents/{name}.md"), mode="subagent", model=model, permission={}, task_permissions={}
    )


def make_repo(tmp, agents, families, edges=None, routing="auto"):
    root = Path(tmp)
    policy = {
        "models": {m: {"family": f, "status": "approved", "evaluation": None} for m, f in families.items()},
        "constraints": {"independence": edges or []},
    }
    profile = {"version": 1, "agents": {n: {"model": m} for n, m in agents.items()}}
    write_json(root / "execution" / "policy.json", policy)
    write_json(root / "execution" / "profiles" / "default.json", profile)
    target = root / "execution" / "routing.json"
    if routing == "auto":
        target.write_bytes(routing_text(render_routing(profile, policy)).encode("utf-8"))
    elif routing is not None:
        target.write_bytes(routing.encode("utf-8"))
    return root


def texts(issues):
    return " | ".join(str(issue) for issue in issues)


class PureChecks(unittest.TestCase):
    def test_coverage_flags_agent_without_entry_and_entry_without_agent(self):
        problems = check_coverage({"a": "m/one", "ghost": "m/one"}, ["a", "b"])
        self.assertEqual([p[0] for p in problems], ["b", "ghost"])
        self.assertIn("F34", problems[0][1])

    def test_coverage_equal_is_clean(self):
        self.assertEqual(check_coverage({"a": "m/one"}, ["a"]), [])

    def test_conflict_flags_a_different_model_line(self):
        problems = check_frontmatter_conflicts({"a": "m/one"}, {"a": "m/two"})
        self.assertEqual(len(problems), 1)
        self.assertIn("F32", problems[0][1])

    def test_conflict_ignores_equal_lines_and_agents_without_a_line(self):
        self.assertEqual(check_frontmatter_conflicts({"a": "m/one", "b": "m/two"}, {"a": "m/one"}), [])

    def test_routing_text_missing_stale_and_current(self):
        self.assertIn("missing", check_routing_text(None, "x")[0])
        self.assertIn("out of date", check_routing_text("y", "x")[0])
        self.assertEqual(check_routing_text("x", "x"), [])


class ResolvedModelReader(unittest.TestCase):
    def test_parses_the_top_level_model_block(self):
        self.assertEqual(parse_resolved_model(SAMPLE), "github-copilot/gpt-5.4-mini")

    def test_no_block_means_no_model(self):
        self.assertIsNone(parse_resolved_model('{\n  "name": "qa"\n}\n'))

    def test_nested_model_blocks_are_ignored(self):
        self.assertIsNone(parse_resolved_model('{\n  "x": {\n    "model": {\n      "modelID": "m"\n    }\n  }\n}\n'))

    def test_find_opencode(self):
        self.assertEqual(find_opencode(which=lambda name: "/x/opencode"), "/x/opencode")
        with self.assertRaises(ResolvedModelError):
            find_opencode(which=lambda name: None)

    def test_fetch_runs_debug_agent_and_parses(self):
        seen = []

        def runner(command, **kwargs):
            seen.append(command)
            return SimpleNamespace(returncode=0, stdout=SAMPLE, stderr="")

        self.assertEqual(fetch_resolved_model("oc", "qa", runner=runner), "github-copilot/gpt-5.4-mini")
        self.assertEqual(seen, [["oc", "debug", "agent", "qa"]])

    def test_fetch_failures_raise(self):
        def bad_exit(command, **kwargs):
            return SimpleNamespace(returncode=1, stdout="", stderr="boom")

        def timeout(command, **kwargs):
            raise subprocess.TimeoutExpired(command, 1)

        with self.assertRaises(ResolvedModelError):
            fetch_resolved_model("oc", "qa", runner=bad_exit)
        with self.assertRaises(ResolvedModelError):
            fetch_resolved_model("oc", "qa", runner=timeout)


class CheckRouting(unittest.TestCase):
    FAMILIES = {"m/one": "x", "m/two": "y"}

    def run_check(self, agents, profile_agents, **kwargs):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_repo(tmp, profile_agents, self.FAMILIES, **kwargs)
            return validate_framework.check_routing(root, agents)

    def test_clean(self):
        issues = self.run_check([agent("a", "m/one"), agent("b")], {"a": "m/one", "b": "m/two"})
        self.assertEqual(issues, [])

    def test_agent_without_entry(self):
        issues = self.run_check([agent("a"), agent("b")], {"a": "m/one"})
        self.assertEqual(len(issues), 1)
        self.assertIn("no profile entry", texts(issues))

    def test_entry_without_agent(self):
        issues = self.run_check([agent("a")], {"a": "m/one", "ghost": "m/two"}, routing="auto")
        self.assertIn("no agent file", texts(issues))

    def test_model_line_that_contradicts_the_profile(self):
        issues = self.run_check([agent("a", "m/two")], {"a": "m/one"})
        self.assertIn("m/two", texts(issues))

    def test_missing_routing_file(self):
        self.assertIn("missing", texts(self.run_check([agent("a")], {"a": "m/one"}, routing=None)))

    def test_stale_routing_file(self):
        self.assertIn("out of date", texts(self.run_check([agent("a")], {"a": "m/one"}, routing="{}\n")))

    def test_model_not_in_policy(self):
        issues = self.run_check([agent("a")], {"a": "m/zzz"}, routing=None)
        self.assertIn("m/zzz", texts(issues))

    def test_invalid_profile_is_one_issue(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_repo(tmp, {"a": "m/one"}, self.FAMILIES)
            (root / "execution" / "profiles" / "default.json").write_text("{bad", encoding="utf-8")
            issues = validate_framework.check_routing(root, [agent("a")])
        self.assertEqual(len(issues), 1)
        self.assertIn("default.json", texts(issues))


class CheckPolicyReadsTheProfile(unittest.TestCase):
    def test_same_family_in_the_profile_is_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_repo(
                tmp,
                {"architect": "m/one", "plan-reviewer": "m/two"},
                {"m/one": "x", "m/two": "x"},
                edges=[EDGE],
            )
            issues = validate_framework.check_policy(root, [])
        self.assertIn("different family", texts(issues))

    def test_different_families_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_repo(
                tmp,
                {"architect": "m/one", "plan-reviewer": "m/two"},
                {"m/one": "x", "m/two": "y"},
                edges=[EDGE],
            )
            self.assertEqual(validate_framework.check_policy(root, []), [])

    def test_missing_profile_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_repo(tmp, {"a": "m/one"}, {"m/one": "x"})
            (root / "execution" / "profiles" / "default.json").unlink()
            issues = validate_framework.check_policy(root, [])
        self.assertEqual(len(issues), 1)
        self.assertIn("default.json", texts(issues))


class CheckResolvedModels(unittest.TestCase):
    def run_check(self, resolved=None, find_error=None, fetch_error=None):
        patches = []
        if find_error:
            patches.append(mock.patch.object(validate_framework, "find_opencode", side_effect=find_error))
        else:
            patches.append(mock.patch.object(validate_framework, "find_opencode", return_value="oc"))
        if fetch_error:
            patches.append(mock.patch.object(validate_framework, "fetch_resolved_model", side_effect=fetch_error))
        else:
            patches.append(mock.patch.object(validate_framework, "fetch_resolved_model", return_value=resolved))
        with tempfile.TemporaryDirectory() as tmp:
            root = make_repo(tmp, {"a": "m/one"}, {"m/one": "x", "m/two": "y"})
            with patches[0], patches[1]:
                return validate_framework.check_resolved_models(root)

    def test_match_is_clean(self):
        self.assertEqual(self.run_check(resolved="m/one"), [])

    def test_different_model_is_flagged(self):
        self.assertIn("m/two", texts(self.run_check(resolved="m/two")))

    def test_no_model_is_flagged_as_inheriting(self):
        self.assertIn("F34", texts(self.run_check(resolved=None)))

    def test_opencode_missing_fails_closed(self):
        issues = self.run_check(find_error=ResolvedModelError("not found"))
        self.assertEqual(len(issues), 1)
        self.assertIn("not found", texts(issues))

    def test_read_error_is_flagged_per_agent(self):
        self.assertIn("boom", texts(self.run_check(fetch_error=ResolvedModelError("boom"))))


if __name__ == "__main__":
    unittest.main()
