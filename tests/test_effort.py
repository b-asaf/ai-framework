"""Tests for the reasoning effort (an OpenCode variant): the profile, the run config, the export check, the record and the benchmark."""

import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tools"))

from execution.runner import benchmark, record, resolve, run  # noqa: E402
from execution.runner import opencode_adapter as adapter  # noqa: E402
from lib import routing  # noqa: E402

FIXTURES = REPO / "tests" / "fixtures" / "opencode-run"
ROLE = "sample-reviewer"
MODEL = "github-copilot/claude-haiku-4.5"
APPROVED = {"family": "Claude", "status": "approved", "evaluation": None}
AGENT_TEXT = "---\ndescription: Fixture\nmode: subagent\npermission:\n  edit: deny\n---\nReview.\n"


def read(name):
    return (FIXTURES / name).read_text(encoding="utf-8")


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def make_repo(base, role=ROLE, model=MODEL, effort=None, models=None):
    root = Path(base) / "repo"
    entry = {"model": model, "effort": effort} if effort else {"model": model}
    policy = {"version": 1, "models": models or {model: APPROVED}, "constraints": {"independence": []}}
    write_json(root / "execution" / "policy.json", policy)
    write_json(root / "execution" / "profiles" / "default.json", {"version": 1, "agents": {role: entry}})
    (root / "agents").mkdir(parents=True)
    (root / "agents" / f"{role}.md").write_text(AGENT_TEXT, encoding="utf-8")
    return root


class Levels(unittest.TestCase):
    def load(self, agents):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "profile.json"
            path.write_text(json.dumps({"version": 1, "agents": agents}), encoding="utf-8")
            return routing.load_profile(path)

    def test_every_known_level_is_accepted_and_anything_else_is_described(self):
        for level in routing.EFFORTS:
            self.assertIsNone(routing.effort_problem(level))
        for bad in ("ultra", "", 3, None, ["high"]):
            self.assertIn("is not one of", routing.effort_problem(bad))

    def test_a_profile_may_name_an_effort_per_agent(self):
        profile = self.load({"a": {"model": "m/one", "effort": "high"}, "b": {"model": "m/two"}})
        self.assertEqual(routing.profile_efforts(profile), {"a": "high"})
        self.assertEqual(routing.profile_models(profile), {"a": "m/one", "b": "m/two"})

    def test_an_unknown_effort_in_a_profile_is_refused_and_names_the_agent(self):
        for bad in ("ultra", 3, ""):
            with self.subTest(effort=bad):
                with self.assertRaisesRegex(routing.ProfileError, "agent 'a'.*effort"):
                    self.load({"a": {"model": "m/one", "effort": bad}})

    def test_the_effort_is_rendered_as_the_variant_of_the_agent(self):
        profile = self.load({"a": {"model": "m/one", "effort": "high"}, "b": {"model": "m/two"}})
        agents = routing.render_routing(profile, {"models": {"m/one": {}, "m/two": {}}})["agent"]
        self.assertEqual(agents, {"a": {"model": "m/one", "variant": "high"}, "b": {"model": "m/two"}})

    def test_agent_entry(self):
        self.assertEqual(routing.agent_entry("m/one"), {"model": "m/one"})
        self.assertEqual(routing.agent_entry("m/one", "max"), {"model": "m/one", "variant": "max"})


class RunConfig(unittest.TestCase):
    def test_an_effort_becomes_the_variant_and_nothing_else_changes(self):
        with_effort = json.loads(adapter.render_run_config({"qa": "m/one"}, {"qa": "high"}))
        self.assertEqual(with_effort["agent"], {"qa": {"model": "m/one", "variant": "high"}})
        plain = adapter.render_run_config({"qa": "m/one"})
        self.assertEqual(plain, adapter.render_run_config({"qa": "m/one"}, {}))
        self.assertNotIn("variant", plain)

    def test_an_unknown_effort_is_refused(self):
        with self.assertRaisesRegex(adapter.AdapterError, "qa: effort 'ultra'"):
            adapter.render_run_config({"qa": "m/one"}, {"qa": "ultra"})

    def test_prepare_run_dir_writes_the_effort(self):
        with tempfile.TemporaryDirectory() as tmp:
            setup = adapter.prepare_run_dir(tmp, "qa", AGENT_TEXT, "m/one", "xhigh")
            agent = json.loads(setup.config_file.read_text(encoding="utf-8"))["agent"]["qa"]
        self.assertEqual(agent, {"model": "m/one", "variant": "xhigh"})


def export_text(**changes):
    info = {"role": "assistant", "agent": ROLE, "providerID": "github-copilot", "modelID": "claude-haiku-4.5", "finish": "stop"}
    info.update(changes)
    return json.dumps({"info": {}, "messages": [{"info": info}]})


class Export(unittest.TestCase):
    def test_the_variant_is_read_from_the_assistant_message(self):
        self.assertEqual(adapter.parse_export(export_text(variant="high")).variant, "high")
        self.assertIsNone(adapter.parse_export(export_text()).variant)
        self.assertIsNone(adapter.parse_export(export_text(variant=3)).variant)

    def test_the_real_sample_has_no_variant(self):
        self.assertIsNone(adapter.parse_export(read("review-session.json")).variant)

    def test_a_requested_effort_must_be_confirmed(self):
        ran = adapter.RanInfo(ROLE, MODEL, "stop", "high")
        self.assertEqual(adapter.check_model_ran(ran, ROLE, MODEL, "high"), [])
        self.assertEqual(adapter.check_model_ran(ran, ROLE, MODEL), [])
        problems = adapter.check_model_ran(adapter.RanInfo(ROLE, MODEL, "stop"), ROLE, MODEL, "xhigh")
        self.assertEqual(len(problems), 1)
        self.assertIn("F52", problems[0])
        self.assertIn("'default'", problems[0])

    def test_assess_fails_a_run_whose_effort_was_not_applied(self):
        events = adapter.parse_events(read("review.jsonl"))
        ran = adapter.parse_export(read("review-session.json"))
        result = adapter.assess(events, "", ran, ROLE, MODEL, effort="high")
        self.assertEqual(result.status, "failure")
        self.assertIn("effort", " ".join(result.problems))
        self.assertIsNone(result.resolved_effort)
        self.assertEqual(adapter.assess(events, "", ran, ROLE, MODEL).status, "success")
        confirmed = adapter.assess(events, "", adapter.RanInfo(ROLE, MODEL, "stop", "high"), ROLE, MODEL, effort="high")
        self.assertEqual((confirmed.status, confirmed.resolved_effort), ("success", "high"))


class Resolve(unittest.TestCase):
    def test_the_effort_of_the_profile_is_resolved(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(resolve.resolve(ROLE, make_repo(tmp, effort="high")).effort, "high")
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(resolve.resolve(ROLE, make_repo(tmp)).effort)

    def test_a_profile_with_an_unknown_effort_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = make_repo(tmp, effort="ultra")
            with self.assertRaisesRegex(resolve.ResolveError, "effort"):
                resolve.resolve(ROLE, repo)


def record_fields(**changes):
    base = dict(
        role=ROLE, profile="default", runtime="opencode", requested_model=MODEL, resolved_model=MODEL,
        policy_result="pass", fallback=False, input_artifacts=[], output_artifacts=[],
        status=record.status_levels("success", "success"), stop_reason="stop", tokens=None, cost=0.01,
        duration_ms=5, verification=None, error=None,
    )
    base.update(changes)
    return base


class Record(unittest.TestCase):
    def test_the_efforts_are_optional_nullable_strings(self):
        self.assertNotIn("requested_effort", record.build_record(**record_fields()))
        built = record.build_record(**record_fields(requested_effort="high", resolved_effort="high"))
        self.assertEqual((built["requested_effort"], built["resolved_effort"]), ("high", "high"))
        nulls = record.build_record(**record_fields(requested_effort=None, resolved_effort=None))
        self.assertIsNone(nulls["resolved_effort"])
        with self.assertRaises(record.RecordError):
            record.build_record(**record_fields(resolved_effort=3))


class Bench(unittest.TestCase):
    MODELS = {"m/one": APPROVED, "m/exp": {"family": "x", "status": "experimental", "evaluation": None}}

    def test_a_spec_is_a_model_and_an_optional_effort(self):
        self.assertEqual(benchmark.split_spec("m/one"), ("m/one", None))
        self.assertEqual(benchmark.split_spec("m/one@high"), ("m/one", "high"))
        self.assertEqual(benchmark.split_spec("m/one@"), ("m/one", None))

    def test_a_bench_root_carries_the_effort_in_its_profile(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = make_repo(tmp, role=benchmark.ROLE, model="m/one", models=self.MODELS)
            root = benchmark.make_bench_root(repo, Path(tmp) / "root", "m/one", "max")
            self.assertEqual(resolve.resolve(benchmark.ROLE, root).effort, "max")

    def test_a_trial_model_is_approved_in_the_bench_root_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = make_repo(tmp, role=benchmark.ROLE, model="m/one", models=self.MODELS)
            plain = benchmark.make_bench_root(repo, Path(tmp) / "plain", "m/exp")
            trial = benchmark.make_bench_root(repo, Path(tmp) / "trial", "m/exp", trial=True)
            with self.assertRaisesRegex(resolve.ResolveError, "experimental"):
                resolve.resolve(benchmark.ROLE, plain)
            self.assertEqual(resolve.resolve(benchmark.ROLE, trial).model, "m/exp")
            repo_policy = json.loads((repo / "execution" / "policy.json").read_text(encoding="utf-8"))
            self.assertEqual(repo_policy["models"]["m/exp"]["status"], "experimental")

    def test_every_spec_runs_on_its_own_root_and_trial_models_are_approved(self):
        seen = []

        def review(root, target, role, diff, timeout=None):
            seen.append(resolve.resolve(role, root))
            raise resolve.ResolveError("stop here")

        with tempfile.TemporaryDirectory() as tmp:
            repo = make_repo(tmp, role=benchmark.ROLE, model="m/one", models=self.MODELS)
            rows = benchmark.run_benchmark(
                repo, ["m/one", "m/one@high", "m/exp"], ["off-by-one-loop"], 1, Path(tmp) / "out",
                review=review, progress=lambda line: None, trial_models={"m/exp"},
            )
        self.assertEqual([row["model"] for row in rows], ["m/one", "m/one@high", "m/exp"])
        self.assertEqual([(r.model, r.effort) for r in seen], [("m/one", None), ("m/one", "high"), ("m/exp", None)])

    def test_the_trial_flag_is_off_by_default(self):
        self.assertTrue(benchmark.build_parser().parse_args(["--trial"]).trial)
        self.assertFalse(benchmark.build_parser().parse_args([]).trial)


class FakeRunner:
    def __init__(self, export):
        self.export, self.routing = export, None

    def __call__(self, command, **kwargs):
        if command[1] == "export":
            return SimpleNamespace(returncode=0, stdout=self.export, stderr="")
        self.routing = json.loads(Path(kwargs["env"]["OPENCODE_CONFIG"]).read_text(encoding="utf-8"))
        return SimpleNamespace(returncode=0, stdout=read("review.jsonl"), stderr="")


class RunWiring(unittest.TestCase):
    def go(self, export):
        with tempfile.TemporaryDirectory() as tmp:
            repo = make_repo(tmp, effort="high")
            target = Path(tmp) / "target"
            (target / "docs" / "project-overview").mkdir(parents=True)
            stack = target / "docs" / "project-overview" / "stack.md"
            stack.write_text("# Stack\n\n- Language: JavaScript\n", encoding="utf-8")
            (target / ".ai-framework.json").write_text("{}", encoding="utf-8")
            diff = Path(tmp) / "case.patch"
            diff.write_text("diff --git a/x b/x\n", encoding="utf-8")
            runner = FakeRunner(export)
            outcome = run.run_review(repo, target, ROLE, diff, runner=runner, environ={"PATH": "p"}, which=lambda name: "oc")
        return outcome, runner

    def test_the_effort_reaches_the_run_config_and_a_confirmed_run_succeeds(self):
        export = json.loads(read("review-session.json"))
        export["messages"][1]["info"]["variant"] = "high"
        outcome, runner = self.go(json.dumps(export))
        self.assertEqual(runner.routing["agent"][ROLE], {"model": MODEL, "variant": "high"})
        built = outcome.record
        self.assertEqual((built["requested_effort"], built["resolved_effort"]), ("high", "high"))
        self.assertEqual(built["status"]["execution"], "success")

    def test_an_effort_the_export_does_not_confirm_fails_the_run(self):
        outcome, _ = self.go(read("review-session.json"))
        built = outcome.record
        self.assertEqual((built["requested_effort"], built["resolved_effort"]), ("high", None))
        self.assertEqual(built["status"]["execution"], "failure")
        self.assertIn("F52", built["error"]["message"])


if __name__ == "__main__":
    unittest.main()
