"""Model routing (step 1b.2, DEC-019).

execution/profiles/default.json is the only place that maps an agent to a
model. render_routing turns it into the config OpenCode reads (the generated
execution/routing.json, linked as config.json). Everything here is a pure
function. A profile that cannot be read or is malformed raises ProfileError;
the caller reports it (fail closed, DEC-015).
"""

import json
from pathlib import Path


class ProfileError(Exception):
    """The model profile is missing, malformed, or names a model the policy does not know."""


def _read_profile_file(path):
    if not path.is_file():
        raise ProfileError(f"{path.as_posix()} not found, so models cannot be routed")
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as error:
        raise ProfileError(f"{path.name} cannot be read: {error}") from error


def _check_profile_entry(name, entry, filename):
    if not isinstance(entry, dict):
        raise ProfileError(f"agent '{name}' in {filename} must be an object")
    model = entry.get("model")
    if not isinstance(model, str) or not model.strip():
        raise ProfileError(f"agent '{name}' in {filename} needs a 'model'")
    capability = entry.get("capability")
    if capability is not None and not isinstance(capability, str):
        raise ProfileError(f"agent '{name}' in {filename}: 'capability' must be a string (documentation only)")


def load_profile(path):
    path = Path(path)
    data = _read_profile_file(path)
    agents = data.get("agents") if isinstance(data, dict) else None
    if not isinstance(agents, dict) or not agents:
        raise ProfileError(f"{path.name} needs a non-empty 'agents' object")
    for name, entry in agents.items():
        _check_profile_entry(name, entry, path.name)
    return data


def profile_models(profile):
    """Map agent name to model id."""
    return {name: entry["model"] for name, entry in profile["agents"].items()}


def render_routing(profile, policy):
    """Return the OpenCode config for the profile. Every model must be in the policy."""
    models = profile_models(profile)
    unknown = [f"{name} ({models[name]})" for name in sorted(models) if models[name] not in policy["models"]]
    if unknown:
        raise ProfileError("model not in the model policy: " + ", ".join(unknown))
    return {"agent": {name: {"model": models[name]} for name in sorted(models)}}


def routing_text(routing):
    """Stable text form: sorted keys, two-space indent, trailing newline."""
    return json.dumps(routing, indent=2, sort_keys=True) + "\n"


def check_profile_matches_agents(profile_by_agent, agent_models):
    """TEMPORARY (removed with the model: lines in step 1b.5).

    Return (agent, message) for each difference between the profile and the
    model: lines still in the agent files.
    """
    problems = []
    for name in sorted(set(profile_by_agent) | set(agent_models)):
        in_profile = profile_by_agent.get(name)
        in_agent = agent_models.get(name)
        if in_profile is None:
            problems.append((name, "agent has no profile entry"))
        elif in_agent is None:
            problems.append((name, "profile entry has no agent file model line to compare"))
        elif in_profile != in_agent:
            problems.append((name, f"profile says '{in_profile}' but the agent file says '{in_agent}'"))
    return problems


def check_coverage(profile_by_agent, agent_names):
    """Return (agent, message) for each agent without a profile entry and each entry without an agent.

    An agent without an entry would run on its caller's model (F34).
    """
    problems = []
    for name in sorted(set(agent_names) - set(profile_by_agent)):
        problems.append((name, "agent has no profile entry; it would run on its caller's model (F34)"))
    for name in sorted(set(profile_by_agent) - set(agent_names)):
        problems.append((name, "profile entry has no agent file"))
    return problems


def check_frontmatter_conflicts(profile_by_agent, agent_models):
    """TEMPORARY (removed with the model: lines in step 1b.5).

    A model: line in an agent file beats the routing (F32), so a line that
    differs from the profile makes the profile wrong.
    """
    return [
        (name, f"profile says '{profile_by_agent[name]}' but the agent file has 'model: {model}', and the file wins (F32)")
        for name, model in sorted(agent_models.items())
        if name in profile_by_agent and profile_by_agent[name] != model
    ]


def check_routing_text(actual, expected):
    """Return messages when the committed routing file is missing (actual is None) or differs from the rendered text."""
    if actual is None:
        return ["execution/routing.json is missing; run: python tools/generate_routing.py"]
    if actual != expected:
        return ["execution/routing.json is out of date; run: python tools/generate_routing.py"]
    return []
