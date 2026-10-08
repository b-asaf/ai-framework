"""Model policy checks (step 1.6, DEC-014, DEC-016).

execution/policy.json holds which models exist, their family and status, and
which agents must stay independent. Everything here is a pure function, so it
is easy to test. A policy that cannot be read or is malformed raises
PolicyError; the caller reports it as an issue (fail closed, DEC-015).

Family names the model lineage (claude, gpt, gemini, opencode) and is
independent of provider.
"""

import json
from pathlib import Path

STATUSES = ("approved", "experimental")
RULES = ("different-family",)


class PolicyError(Exception):
    """The model policy is missing or malformed."""


def load_policy(path):
    path = Path(path)
    if not path.is_file():
        raise PolicyError(f"{path.as_posix()} not found, so the model policy cannot be checked")
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as error:
        raise PolicyError(f"{path.name} cannot be read: {error}") from error
    if not isinstance(data, dict) or not isinstance(data.get("models"), dict):
        raise PolicyError(f"{path.name} needs a 'models' object")
    constraints = data.get("constraints")
    if not isinstance(constraints, dict) or not isinstance(constraints.get("independence"), list):
        raise PolicyError(f"{path.name} needs a 'constraints.independence' list")
    for model, entry in data["models"].items():
        if not isinstance(entry, dict) or not entry.get("family"):
            raise PolicyError(f"model '{model}' in {path.name} needs a 'family'")
        if entry.get("status") not in STATUSES:
            raise PolicyError(
                f"model '{model}' in {path.name} has status {entry.get('status')!r}; "
                f"expected one of {', '.join(STATUSES)}"
            )
    for edge in constraints["independence"]:
        if not isinstance(edge, dict) or not edge.get("producer") or not edge.get("validator"):
            raise PolicyError(f"each independence edge in {path.name} needs a producer and a validator")
    return data


def check_experimental(agent_models, policy, repo_root):
    """Return (agent, message) for each agent on a model that is unknown or experimental without an evaluation."""
    problems = []
    models = policy["models"]
    for name in sorted(agent_models):
        model = agent_models[name]
        entry = models.get(model)
        if entry is None:
            problems.append((name, f"model '{model}' is not in the model policy"))
            continue
        if entry["status"] != "experimental":
            continue
        evaluation = entry.get("evaluation")
        if not evaluation:
            problems.append(
                (
                    name,
                    f"model '{model}' is experimental and has no evaluation record; "
                    "evaluate and promote it first (DEC-014)",
                )
            )
        elif not (Path(repo_root) / evaluation).is_file():
            problems.append(
                (name, f"model '{model}' names evaluation '{evaluation}', but that file does not exist")
            )
    return problems


def check_independence(agent_models, policy):
    """Return (label, message) for each independence edge that is broken or cannot be decided."""
    problems = []
    models = policy["models"]
    for edge in policy["constraints"]["independence"]:
        producer, validator = edge["producer"], edge["validator"]
        label = f"{producer} -> {validator}"
        rule = edge.get("rule", "different-family")
        if rule not in RULES:
            problems.append((label, f"unknown rule '{rule}'"))
            continue
        missing = [name for name in (producer, validator) if name not in agent_models]
        if missing:
            problems.append((label, "agent not found or without a model: " + ", ".join(missing)))
            continue
        families = []
        for name in (producer, validator):
            entry = models.get(agent_models[name])
            if entry is None:
                problems.append((label, f"model '{agent_models[name]}' of '{name}' is not in the model policy"))
                break
            families.append(entry["family"].lower())
        else:
            if families[0] == families[1]:
                problems.append(
                    (
                        label,
                        f"both use family '{families[0]}' (models '{agent_models[producer]}' and "
                        f"'{agent_models[validator]}'); the validator must be in a different family than the producer",
                    )
                )
    return problems
