import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tools"))

import validate_agents  # noqa: E402
from lib.policy import (  # noqa: E402
    PolicyError,
    check_experimental,
    check_independence,
    load_policy,
)

CATALOG = "docs/decisions/MODEL-ASSIGNMENT-MATRIX.md"
MATRIX = REPO / CATALOG
POLICY = REPO / "execution" / "policy.json"


def make_policy(models=None, edges=None):
    return {
        "models": models or {},
        "constraints": {"independence": edges or []},
    }


def model(family, status="approved", evaluation=None):
    return {"family": family, "status": status, "evaluation": evaluation}


EDGE = {"producer": "architect", "validator": "plan-reviewer", "rule": "different-family"}


class CheckExperimental(unittest.TestCase):
    def test_experimental_without_evaluation_is_flagged(self):
        policy = make_policy({"m/sol": model("gpt", "experimental")})
        problems = check_experimental({"code-reviewer": "m/sol"}, policy, REPO)
        self.assertEqual(len(problems), 1)
        self.assertEqual(problems[0][0], "code-reviewer")
        self.assertIn("no evaluation record", problems[0][1])

    def test_experimental_with_existing_evaluation_passes(self):
        with tempfile.TemporaryDirectory() as folder:
            evaluation = Path(folder) / "docs" / "decisions" / "evaluations" / "sol.md"
            evaluation.parent.mkdir(parents=True)
            evaluation.write_text("evaluated", encoding="utf-8")
            policy = make_policy(
                {"m/sol": model("gpt", "experimental", "docs/decisions/evaluations/sol.md")}
            )
            self.assertEqual(check_experimental({"a": "m/sol"}, policy, folder), [])

    def test_missing_evaluation_file_is_flagged(self):
        policy = make_policy({"m/sol": model("gpt", "experimental", "docs/nope.md")})
        problems = check_experimental({"a": "m/sol"}, policy, REPO)
        self.assertEqual(len(problems), 1)
        self.assertIn("does not exist", problems[0][1])

    def test_approved_model_passes(self):
        policy = make_policy({"m/ok": model("claude")})
        self.assertEqual(check_experimental({"a": "m/ok"}, policy, REPO), [])

    def test_unknown_model_is_flagged(self):
        problems = check_experimental({"a": "m/ghost"}, make_policy(), REPO)
        self.assertEqual(len(problems), 1)
        self.assertIn("not in the model policy", problems[0][1])


class CheckIndependence(unittest.TestCase):
    def policy(self):
        return make_policy({"m/a": model("gpt"), "m/b": model("claude"), "m/c": model("GPT")}, [EDGE])

    def test_different_families_pass(self):
        self.assertEqual(check_independence({"architect": "m/a", "plan-reviewer": "m/b"}, self.policy()), [])

    def test_same_model_is_flagged(self):
        problems = check_independence({"architect": "m/a", "plan-reviewer": "m/a"}, self.policy())
        self.assertEqual(len(problems), 1)
        self.assertEqual(problems[0][0], "architect -> plan-reviewer")
        self.assertIn("family 'gpt'", problems[0][1])

    def test_same_family_other_model_is_flagged_case_insensitively(self):
        problems = check_independence({"architect": "m/a", "plan-reviewer": "m/c"}, self.policy())
        self.assertEqual(len(problems), 1)

    def test_missing_agent_is_flagged(self):
        problems = check_independence({"architect": "m/a"}, self.policy())
        self.assertEqual(len(problems), 1)
        self.assertIn("plan-reviewer", problems[0][1])

    def test_model_missing_from_policy_is_flagged(self):
        problems = check_independence({"architect": "m/a", "plan-reviewer": "m/ghost"}, self.policy())
        self.assertEqual(len(problems), 1)
        self.assertIn("not in the model policy", problems[0][1])

    def test_unknown_rule_fails_closed(self):
        edge = dict(EDGE, rule="different-planet")
        policy = make_policy({"m/a": model("gpt")}, [edge])
        problems = check_independence({"architect": "m/a", "plan-reviewer": "m/a"}, policy)
        self.assertEqual(len(problems), 1)
        self.assertIn("unknown rule", problems[0][1])


class LoadPolicy(unittest.TestCase):
    def write(self, folder, data):
        path = Path(folder) / "policy.json"
        path.write_text(data if isinstance(data, str) else json.dumps(data), encoding="utf-8")
        return path

    def test_missing_file_fails_closed(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(PolicyError) as caught:
                load_policy(Path(folder) / "policy.json")
            self.assertIn("not found", str(caught.exception))

    def test_invalid_json_is_reported(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(PolicyError):
                load_policy(self.write(folder, "{not json"))

    def test_missing_sections_are_reported(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(PolicyError):
                load_policy(self.write(folder, {"models": {}}))

    def test_unknown_status_is_reported(self):
        with tempfile.TemporaryDirectory() as folder:
            data = make_policy({"m/a": {"family": "gpt", "status": "maybe"}})
            with self.assertRaises(PolicyError) as caught:
                load_policy(self.write(folder, data))
            self.assertIn("status", str(caught.exception))

    def test_valid_policy_loads(self):
        with tempfile.TemporaryDirectory() as folder:
            data = make_policy({"m/a": model("gpt")}, [EDGE])
            self.assertEqual(load_policy(self.write(folder, data))["models"]["m/a"]["family"], "gpt")


class ValidatorFixtures(unittest.TestCase):
    def run_validator(self, fixture):
        env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
        return subprocess.run(
            [sys.executable, str(REPO / "tools" / "validate_agents.py"),
             "tests/fixtures/" + fixture, CATALOG],
            cwd=REPO, env=env, capture_output=True,
            encoding="utf-8", errors="replace",
        )

    def test_same_model_for_planner_and_reviewer_fails(self):
        result = self.run_validator("dec014-same-model")
        output = result.stdout + result.stderr
        self.assertEqual(result.returncode, 1, output)
        self.assertIn("[independence] architect -> plan-reviewer", output)

    def test_experimental_model_without_evaluation_fails(self):
        result = self.run_validator("dec014-experimental")
        output = result.stdout + result.stderr
        self.assertEqual(result.returncode, 1, output)
        self.assertIn("[experimental] code-reviewer", output)
        self.assertIn("gpt-6-sol", output)

    def test_valid_policy_fixture_has_no_policy_issue(self):
        result = self.run_validator("policy-ok")
        output = result.stdout + result.stderr
        self.assertNotIn("[independence]", output)
        self.assertNotIn("[experimental]", output)
        self.assertNotIn("[policy]", output)

    def test_fixture_without_policy_reports_it(self):
        result = self.run_validator("read-only-ok")
        self.assertIn("[policy] (policy)", result.stdout + result.stderr)


class RealPolicy(unittest.TestCase):
    """Until step 4.3 generates the matrix, the matrix and the policy must agree."""

    def test_models_and_families_match_the_matrix(self):
        policy = load_policy(POLICY)
        catalog = validate_agents.load_model_catalog_from_markdown(MATRIX)
        self.assertEqual(set(policy["models"]), set(catalog))
        for model_id, entry in policy["models"].items():
            self.assertEqual(entry["family"].lower(), catalog[model_id].lower(), model_id)

    def test_independence_edges_match_the_matrix(self):
        policy = load_policy(POLICY)
        from_policy = {(e["producer"], e["validator"]) for e in policy["constraints"]["independence"]}
        from_matrix = set()
        for table in validate_agents._parse_markdown_tables(MATRIX.read_text(encoding="utf-8-sig")):
            header, *rows = table
            cols = [validate_agents._find_column(header, name) for name in ("producer", "validator", "required")]
            if None in cols:
                continue
            for row in rows:
                if validate_agents._is_separator_row(row) or len(row) <= max(cols):
                    continue
                if row[cols[2]].strip().upper() == "YES":
                    from_matrix.add((row[cols[0]], row[cols[1]]))
        self.assertEqual(from_policy, from_matrix)


if __name__ == "__main__":
    unittest.main()
