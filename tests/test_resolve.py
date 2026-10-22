import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from execution.runner import resolve as resolver  # noqa: E402
from lib.routing import load_profile, profile_models  # noqa: E402

APPROVED = {"family": "Claude", "status": "approved", "evaluation": None}


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def make_repo(tmp, agents, models, profile_name="default"):
    root = Path(tmp)
    policy = {"version": 1, "models": models, "constraints": {"independence": []}}
    write_json(root / "execution" / "policy.json", policy)
    profile = {"version": 1, "agents": {name: {"model": model} for name, model in agents.items()}}
    write_json(root / "execution" / "profiles" / f"{profile_name}.json", profile)
    return root


class Resolve(unittest.TestCase):
    def test_an_approved_model_resolves_with_a_lowercase_family(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_repo(tmp, {"qa": "m/one"}, {"m/one": APPROVED})
            result = resolver.resolve("qa", root)
        self.assertEqual(
            result, resolver.Resolved(role="qa", profile="default", model="m/one", family="claude", status="approved")
        )

    def test_a_role_without_a_profile_entry_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_repo(tmp, {"qa": "m/one"}, {"m/one": APPROVED})
            with self.assertRaisesRegex(resolver.ResolveError, "F34"):
                resolver.resolve("ghost", root)

    def test_a_model_not_in_the_policy_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_repo(tmp, {"qa": "m/zzz"}, {"m/one": APPROVED})
            with self.assertRaisesRegex(resolver.ResolveError, "m/zzz.*not in the model policy"):
                resolver.resolve("qa", root)

    def test_an_experimental_model_without_an_evaluation_is_rejected(self):
        models = {"m/exp": {"family": "x", "status": "experimental", "evaluation": None}}
        with tempfile.TemporaryDirectory() as tmp:
            root = make_repo(tmp, {"qa": "m/exp"}, models)
            with self.assertRaisesRegex(resolver.ResolveError, "DEC-014"):
                resolver.resolve("qa", root)

    def test_an_experimental_model_with_an_evaluation_file_resolves(self):
        models = {"m/exp": {"family": "x", "status": "experimental", "evaluation": "tests/bench/eval.md"}}
        with tempfile.TemporaryDirectory() as tmp:
            root = make_repo(tmp, {"qa": "m/exp"}, models)
            (root / "tests" / "bench").mkdir(parents=True)
            (root / "tests" / "bench" / "eval.md").write_text("evidence", encoding="utf-8")
            self.assertEqual(resolver.resolve("qa", root).status, "experimental")

    def test_an_evaluation_file_that_does_not_exist_is_rejected(self):
        models = {"m/exp": {"family": "x", "status": "experimental", "evaluation": "tests/bench/missing.md"}}
        with tempfile.TemporaryDirectory() as tmp:
            root = make_repo(tmp, {"qa": "m/exp"}, models)
            with self.assertRaisesRegex(resolver.ResolveError, "does not exist"):
                resolver.resolve("qa", root)

    def test_a_missing_profile_file_is_rejected_and_names_the_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_repo(tmp, {"qa": "m/one"}, {"m/one": APPROVED})
            with self.assertRaisesRegex(resolver.ResolveError, "other.json"):
                resolver.resolve("qa", root, "other")

    def test_a_malformed_policy_is_rejected_and_names_the_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_repo(tmp, {"qa": "m/one"}, {"m/one": APPROVED})
            (root / "execution" / "policy.json").write_text("{bad", encoding="utf-8")
            with self.assertRaisesRegex(resolver.ResolveError, "policy.json"):
                resolver.resolve("qa", root)

    def test_a_profile_name_that_is_a_path_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_repo(tmp, {"qa": "m/one"}, {"m/one": APPROVED})
            with self.assertRaisesRegex(resolver.ResolveError, "profile name"):
                resolver.resolve("qa", root, "../x")

    def test_another_profile_can_route_the_same_role_differently(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_repo(tmp, {"qa": "m/one"}, {"m/one": APPROVED, "m/two": dict(APPROVED, family="gpt")})
            write_json(
                root / "execution" / "profiles" / "bench.json",
                {"version": 1, "agents": {"qa": {"model": "m/two"}}},
            )
            self.assertEqual(resolver.resolve("qa", root).model, "m/one")
            result = resolver.resolve("qa", root, "bench")
        self.assertEqual((result.model, result.family, result.profile), ("m/two", "gpt", "bench"))


class RealRepo(unittest.TestCase):
    def test_every_role_in_the_real_profile_resolves(self):
        roles = sorted(profile_models(load_profile(REPO / "execution" / "profiles" / "default.json")))
        self.assertTrue(roles)
        for role in roles:
            with self.subTest(role=role):
                self.assertEqual(resolver.resolve(role, REPO).role, role)


if __name__ == "__main__":
    unittest.main()
