"""Checks for opencode.json permission blocks (step 1.9, F9).

In OpenCode the last matching rule wins. A catch-all ("*") placed after the
specific rules therefore overrides every one of them: the git allows turn into
prompts, which a headless run auto-rejects, and the denies turn into prompts
as well. The catch-all must come first in each permission block.
"""

import json
from pathlib import Path


class ConfigError(Exception):
    """opencode.json cannot be read."""


def load_config(path):
    path = Path(path)
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as error:
        raise ConfigError(f"{path.name} cannot be read: {error}") from error
    if not isinstance(data, dict):
        raise ConfigError(f"{path.name} must contain a JSON object")
    return data


def catch_all_problems(permission):
    """Return one message per permission block whose '*' rule is not first."""
    problems = []
    if not isinstance(permission, dict):
        return problems
    for category, block in permission.items():
        if not isinstance(block, dict) or "*" not in block:
            continue
        keys = list(block)
        if keys[0] != "*":
            problems.append(
                f"permission.{category}: the '*' rule is number {keys.index('*') + 1} of {len(keys)}; "
                "it must be first, because the last matching rule wins and a later catch-all "
                "overrides the specific rules before it (F9)"
            )
    return problems


def agent_model_problems(config):
    """Return one message per agent whose model is set in opencode.json (check b, DEC-019).

    The model of an agent comes only from the profile. A model in opencode.json
    sits above the generated config.json (F35), so it would silently override
    the profile.
    """
    agents = config.get("agent")
    if not isinstance(agents, dict):
        return []
    return [
        f"agent.{name}.model is set; the model belongs in execution/profiles/default.json "
        "and this entry would override the generated routing (F35)"
        for name, entry in sorted(agents.items())
        if isinstance(entry, dict) and "model" in entry
    ]
