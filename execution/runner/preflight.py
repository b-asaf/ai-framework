"""Preflight for a review run (Phase 2, plan step 2.2, decision #4).

run_review calls require() before anything is written or started. A run on a
project that could change the routing, or on one the framework has not been set
up for, fails here with a message that lists every problem, instead of running
on the wrong model or stopping at a gate (F8, F14). Only the file reads are
impure. A file that exists but cannot be read counts as a problem (fail closed,
DEC-015).

Flagged in the target project: an agent model in opencode.json or
.opencode/opencode.json (F35, F41), an agent file for the role in
.opencode/agents (F40), and a jsonc config, which cannot be checked. The same
agent-model check applies to the file named by OPENCODE_CONFIG in the caller's
environment. The first-run files are required too: docs/project-overview/stack.md
with content (F8) and .ai-framework.json (F14).
"""

import json
import os
from pathlib import Path

CONFIG_FILES = ("opencode.json", ".opencode/opencode.json")
UNCHECKABLE_CONFIG_FILES = ("opencode.jsonc", ".opencode/opencode.jsonc")
AGENT_DIRS = (".opencode/agents", ".opencode/agent")
STACK = "docs/project-overview/stack.md"
FRAMEWORK_CONFIG = ".ai-framework.json"
PLACEHOLDER = "[XXX]"
HINT = "run the first-run analysis in the target project"


class PreflightError(Exception):
    """The target project is not ready for a run."""


def _load_object(path, label):
    """(data, None) for a JSON object, or (None, problem)."""
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as error:
        return None, f"{label} cannot be read: {error}"
    if not isinstance(data, dict):
        return None, f"{label} must be a JSON object"
    return data, None


def _agents_with_a_model(config):
    agents = config.get("agent")
    if not isinstance(agents, dict):
        return []
    return sorted(name for name, entry in agents.items() if isinstance(entry, dict) and "model" in entry)


def _check_config(path, label):
    if not path.is_file():
        return []
    data, problem = _load_object(path, label)
    if problem:
        return [problem]
    return [
        f"{label} sets agent.{name}.model, which would beat the framework routing (F35, decision #4)"
        for name in _agents_with_a_model(data)
    ]


def _check_configs(target):
    problems = []
    for label in CONFIG_FILES:
        problems += _check_config(target / label, label)
    for label in UNCHECKABLE_CONFIG_FILES:
        if (target / label).is_file():
            problems.append(f"{label} cannot be checked for agent models; use opencode.json instead")
    return problems


def _check_agent_file(target, role):
    return [
        f"{label}/{role}.md exists: its model: line would beat the routing and its other fields "
        "would merge into the agent (F40)"
        for label in AGENT_DIRS
        if (target / label / f"{role}.md").is_file()
    ]


def _check_environment(environ):
    value = environ.get("OPENCODE_CONFIG")
    return _check_config(Path(value), "the OPENCODE_CONFIG file") if value else []


def _check_stack(target):
    path = target / STACK
    if not path.is_file():
        return [f"{STACK} is missing; {HINT} (F8)"]
    try:
        text = path.read_text(encoding="utf-8-sig")
    except (OSError, ValueError) as error:
        return [f"{STACK} cannot be read: {error}"]
    if PLACEHOLDER in text:
        return [f"{STACK} still contains {PLACEHOLDER}; {HINT} (F8)"]
    if not [line for line in text.splitlines() if line.strip() and not line.lstrip().startswith("#")]:
        return [f"{STACK} has no content beyond headings; {HINT} (F8)"]
    return []


def _check_framework_config(target):
    path = target / FRAMEWORK_CONFIG
    if not path.is_file():
        return [f"{FRAMEWORK_CONFIG} is missing; {HINT} (F14)"]
    _, problem = _load_object(path, FRAMEWORK_CONFIG)
    return [problem] if problem else []


def check_target(target, role, environ=None):
    """Return one message per reason the target is not ready for a run of this role."""
    target = Path(target)
    if not target.is_dir():
        return [f"target {target.as_posix()} is not a folder"]
    environ = os.environ if environ is None else environ
    return (
        _check_stack(target)
        + _check_framework_config(target)
        + _check_configs(target)
        + _check_agent_file(target, role)
        + _check_environment(environ)
    )


def require(target, role, environ=None):
    """Raise PreflightError listing every problem, or return when the target is ready."""
    problems = check_target(target, role, environ)
    if problems:
        raise PreflightError(
            "the target project is not ready for a run:\n" + "\n".join(f"  - {problem}" for problem in problems)
        )
