"""OpenCode adapter: what a headless run leaves behind (Phase 2, plan step 2.1, section 5.7).

OpenCode-specific knowledge lives here. `opencode run --format json` exits 0
even when the agent did nothing (F2), so success is read from the events: a
text event, a last stop reason of "stop" and no error event. A subagent started
with --agent falls back to the default agent and only warns on stderr (F6), and
a model that is not the requested one must fail the run (F34), so the adapter
also reads the assistant message of `opencode export`, which records the agent
and the model that really ran. An error event (real sample: bad-model.jsonl)
keeps its text in error.data.message. OpenCode repeats the same error, so each
distinct message is listed once.

Everything here is a pure function except the two file helpers at the end
(load_agent_text and prepare_run_dir). Running OpenCode is a later slice. The
sample files in tests/fixtures/opencode-run/ come from real runs.
"""

import json
import re
from dataclasses import dataclass
from pathlib import Path

from . import resolve as _tools_path  # noqa: F401  (puts tools/ on sys.path, as resolve.py does)
from lib.routing import SCHEMA_URL, agent_entry, effort_problem, routing_text  # noqa: E402

FALLBACK = re.compile(r"Falling back to default agent", re.I)
EVENT_CHARS = 500


class AdapterError(Exception):
    """OpenCode output could not be read."""


@dataclass(frozen=True)
class RunEvents:
    session_id: str | None
    reply: str | None
    reason: str | None
    tokens: dict | None
    cost: float | None
    errors: tuple
    bad_lines: int


@dataclass(frozen=True)
class RanInfo:
    agent: str | None
    model: str | None
    finish: str | None
    variant: str | None = None
    directory: str | None = None


@dataclass(frozen=True)
class Assessment:
    """The execution level of a run, with the values a RunRecord needs."""

    status: str
    problems: tuple
    fallback: bool
    resolved_model: str | None
    stop_reason: str | None
    tokens: dict | None
    cost: float | None
    reply: str | None
    resolved_effort: str | None = None


def _is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _add(total, extra):
    """Add the numbers of one nested dict into another."""
    for key, value in extra.items():
        if isinstance(value, dict):
            total[key] = _add(total.get(key, {}), value)
        elif _is_number(value):
            total[key] = total.get(key, 0) + value
    return total


def _load_events(text):
    events, bad = [], 0
    for line in str(text).splitlines():
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except ValueError:
            event = None
        if isinstance(event, dict):
            events.append(event)
        else:
            bad += 1
    return events, bad


def _part(event):
    part = event.get("part")
    return part if isinstance(part, dict) else {}


def _last(events, kind, key, expected):
    values = [_part(event).get(key) for event in events if event.get("type") == kind]
    values = [value for value in values if isinstance(value, expected)]
    return values[-1] if values else None


def _finish_parts(events):
    return [_part(event) for event in events if event.get("type") == "step_finish"]


def _total_tokens(events):
    total, seen = {}, False
    for part in _finish_parts(events):
        if isinstance(part.get("tokens"), dict):
            total, seen = _add(total, part["tokens"]), True
    return total if seen else None


def _total_cost(events):
    costs = [part["cost"] for part in _finish_parts(events) if _is_number(part.get("cost"))]
    return sum(costs) if costs else None


def _error_message(event):
    error = event.get("error")
    data = error.get("data") if isinstance(error, dict) else None
    message = data.get("message") if isinstance(data, dict) else None
    if isinstance(message, str) and message.strip():
        return message.strip()[:EVENT_CHARS]
    return json.dumps(event)[:EVENT_CHARS]


def _error_messages(events):
    """One message per distinct error event, in order."""
    messages = [_error_message(event) for event in events if event.get("type") == "error"]
    return tuple(dict.fromkeys(messages))


def parse_events(text):
    """Read the JSON event stream of `opencode run --format json`.

    The reply is the last text event, the stop reason is the last step_finish,
    and tokens and cost are summed over all steps.
    """
    events, bad = _load_events(text)
    return RunEvents(
        session_id=next((e["sessionID"] for e in events if isinstance(e.get("sessionID"), str)), None),
        reply=_last(events, "text", "text", str),
        reason=_last(events, "step_finish", "reason", str),
        tokens=_total_tokens(events),
        cost=_total_cost(events),
        errors=_error_messages(events),
        bad_lines=bad,
    )


def fallback_warnings(stderr):
    """Return the stderr lines that say OpenCode fell back to the default agent (F6)."""
    return [line.strip() for line in str(stderr).splitlines() if FALLBACK.search(line)]


def _load_export(text):
    raw = str(text)
    start = raw.find("{")
    try:
        data = json.loads(raw[start:]) if start >= 0 else None
    except ValueError as error:
        raise AdapterError(f"the session export is not JSON: {error}") from error
    if not isinstance(data, dict) or not isinstance(data.get("messages"), list):
        raise AdapterError("the session export has no messages")
    return data


def _assistant_infos(data):
    infos = [message.get("info") for message in data["messages"] if isinstance(message, dict)]
    return [info for info in infos if isinstance(info, dict) and info.get("role") == "assistant"]


def _model_id(info):
    provider, model = info.get("providerID"), info.get("modelID")
    return f"{provider}/{model}" if isinstance(provider, str) and isinstance(model, str) else None


def _directory(data, info):
    """The folder the session ran in: the assistant message's cwd, else the session's directory (F74)."""
    path = info.get("path")
    cwd = path.get("cwd") if isinstance(path, dict) else None
    session = data.get("info")
    fallback = session.get("directory") if isinstance(session, dict) else None
    chosen = cwd or fallback
    return chosen if isinstance(chosen, str) and chosen else None


def parse_export(text):
    """Read the agent and the model that ran from the last assistant message of `opencode export`."""
    data = _load_export(text)
    infos = _assistant_infos(data)
    if not infos:
        raise AdapterError("the session export has no assistant message, so the model that ran is unknown")
    info = infos[-1]
    variant = info.get("variant") if isinstance(info.get("variant"), str) else None
    return RanInfo(
        agent=info.get("agent"),
        model=_model_id(info),
        finish=info.get("finish"),
        variant=variant,
        directory=_directory(data, info),
    )


def check_model_ran(ran, agent, model, effort=None):
    """Return one message per difference between what ran and what was requested."""
    problems = []
    if ran.agent != agent:
        problems.append(f"the run used agent '{ran.agent}', not '{agent}': OpenCode fell back to another agent (F6)")
    if ran.model != model:
        problems.append(f"the run used model '{ran.model}', not the requested '{model}' (F34)")
    if effort is not None and ran.variant != effort:
        problems.append(
            f"the run used effort '{ran.variant or 'default'}', not the requested '{effort}': "
            "OpenCode ignores an effort the model does not offer, without a warning (F52)"
        )
    return problems


REJECTED = re.compile(r"permission requested: (\w+) \((.*?)\); auto-rejecting", re.S)
SHOWN_CHARS = 100


def check_directory(ran, directory):
    """One message when the session did not run in the requested folder, or does not say where it ran (F74)."""
    if directory is None:
        return []
    if not ran.directory:
        return ["the session export names no directory, so where the agent worked is unknown (F74)"]
    try:
        same = Path(ran.directory).samefile(directory)
    except (OSError, ValueError):
        same = False
    if same:
        return []
    return [f"the run worked in '{ran.directory}', not in the requested '{Path(directory).as_posix()}' (F74)"]


def rejected_permissions(stderr):
    """The permission requests a headless run auto-rejected, each once and in order, as 'name (argument)' (F13)."""
    found = []
    for name, argument in REJECTED.findall(str(stderr)):
        shown = f"{name} ({' '.join(argument.split())[:SHOWN_CHARS]})"
        if shown not in found:
            found.append(shown)
    return found


def _rejection_problems(stderr):
    rejected = rejected_permissions(stderr)
    if not rejected:
        return []
    return [
        "a permission request was auto-rejected, which ends a headless run without a reply: "
        + "; ".join(rejected)
        + " (F13, F75)"
    ]


def _event_problems(events):
    problems = []
    if events.reply is None:
        problems.append("no text event: the agent produced no reply (F2)")
    if events.reason != "stop":
        problems.append(f"the run did not stop normally (stop reason: {events.reason})")
    problems += [f"error event: {text}" for text in events.errors]
    if events.bad_lines:
        problems.append(f"{events.bad_lines} output line(s) are not JSON events")
    return problems


def _fell_back(warnings, ran, agent):
    return bool(warnings) or (ran is not None and ran.agent != agent)


def assess(events, stderr, ran, agent, model, exit_code=0, effort=None, directory=None):
    """The execution level of a run: success only when nothing above went wrong.

    A fallback, a model mismatch and a non-zero exit code count as failures. The
    result keeps the model that really ran, so the record shows why. ran is None
    when the session export was not read, as after a run that failed before any
    reply; a run that looks fine otherwise but has no export fails closed (F34).
    When a directory is given, the export must say the run worked there (F74). A failed run
    also names the permission requests that OpenCode auto-rejected (F13).
    """
    warnings = fallback_warnings(stderr)
    problems = _event_problems(events)
    if exit_code != 0:
        problems.append(f"OpenCode exited with code {exit_code}")
    problems += [f"stderr: {warning}" for warning in warnings]
    if ran is not None:
        problems += check_model_ran(ran, agent, model, effort) + check_directory(ran, directory)
    elif not problems:
        problems.append("the session export was not read, so the model that ran is unknown (F34)")
    problems += _rejection_problems(stderr) if problems else []
    return Assessment(
        status="failure" if problems else "success",
        problems=tuple(problems),
        fallback=_fell_back(warnings, ran, agent),
        resolved_model=ran.model if ran else None,
        stop_reason=events.reason,
        tokens=events.tokens,
        cost=events.cost,
        reply=events.reply,
        resolved_effort=ran.variant if ran else None,
    )


# Starting a run (plan step 2.1). A subagent started with --agent falls back (F6),
# and an agent.<name>.mode entry in a config is ignored (checked on 1.19.3), so a
# run uses a primary-mode copy of the agent, found through a per-run
# OPENCODE_CONFIG_DIR (a same-name file there beats the global one). The model
# comes from a per-run OPENCODE_CONFIG file (F33, F35), never from the copy.

ROLE_NAME = re.compile(r"[A-Za-z0-9_-]+")
UNSAFE_MESSAGE = re.compile("[\"'|&<>^%{}\\r\\n]")


@dataclass(frozen=True)
class RunSetup:
    config_file: Path
    config_dir: Path


def _check_role(name):
    if not isinstance(name, str) or not ROLE_NAME.fullmatch(name):
        raise AdapterError(f"agent name {name!r} may only use letters, digits, '-' and '_'")


def _frontmatter_end(lines):
    """Index of the closing --- line of the frontmatter."""
    if not lines or lines[0].lstrip("\ufeff").strip() != "---":
        raise AdapterError("the agent file has no frontmatter")
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            return index
    raise AdapterError("the agent file frontmatter is not closed")


def _top_level(lines, end, key):
    """Indexes of the frontmatter lines that start with `key:` at column 0."""
    return [index for index in range(1, end) if lines[index].startswith(key + ":")]


def derive_agent(text):
    """The agent file as a primary agent: only the top-level mode line changes.

    No model line is added, because the model comes from the run config
    (DEC-019). A file that has one is refused, because a model line beats the
    config (F32).
    """
    lines = text.splitlines(keepends=True)
    end = _frontmatter_end(lines)
    if _top_level(lines, end, "model"):
        raise AdapterError("the agent file has a model: line; the model belongs in the profile (DEC-019)")
    modes = _top_level(lines, end, "mode")
    if len(modes) != 1:
        raise AdapterError(f"the agent file needs exactly one top-level mode: line, found {len(modes)}")
    line = lines[modes[0]]
    lines[modes[0]] = "mode: primary" + line[len(line.rstrip("\r\n")):]
    return "".join(lines)


def check_message(message):
    """The task message must survive the Windows shim (F10): plain text on one line."""
    if not isinstance(message, str) or not message.strip():
        raise AdapterError("the task message must be non-empty text")
    if UNSAFE_MESSAGE.search(message):
        raise AdapterError("the task message may not contain quotes, pipes, braces or line breaks (F10)")
    return message


def build_command(executable, agent, message, files):
    """The `opencode run` command. The message comes first: -f takes several values and would swallow it."""
    _check_role(agent)
    command = [str(executable), "run", check_message(message), "--agent", agent, "--format", "json"]
    for path in files:
        command += ["-f", Path(path).as_posix()]
    return command


def build_environment(base, config_file, config_dir):
    """A copy of the environment that points OpenCode at the per-run config file and folder."""
    environment = dict(base)
    environment["OPENCODE_CONFIG"] = Path(config_file).as_posix()
    environment["OPENCODE_CONFIG_DIR"] = Path(config_dir).as_posix()
    return environment


def _checked_efforts(efforts):
    """The efforts of a run config, or AdapterError when one is not a known level."""
    efforts = efforts or {}
    problems = [f"{role}: {effort_problem(effort)}" for role, effort in sorted(efforts.items()) if effort_problem(effort)]
    if problems:
        raise AdapterError("; ".join(problems))
    return efforts


TEMPLATE_READ = "*skills*project-overview*"


def render_run_config(models, efforts=None, headless=False):
    """The OpenCode config for a run: the same format as the generated execution/routing.json.

    headless adds the rule that a run started by the runner may not read the generic project-overview
    template (F77): the skill text points at it, a read outside the project asks, and an ask that nobody
    can answer ends the run without a reply (F13). The committed routing file has no such rule.
    """
    if not isinstance(models, dict) or not models:
        raise AdapterError("a run config needs at least one role and model")
    bad = [role for role, model in models.items() if not isinstance(model, str) or not model.strip()]
    if bad:
        raise AdapterError("no model given for: " + ", ".join(sorted(map(str, bad))))
    efforts = _checked_efforts(efforts)
    agents = {role: agent_entry(models[role], efforts.get(role)) for role in sorted(models)}
    config = {"$schema": SCHEMA_URL, "agent": agents}
    if headless:
        config["permission"] = {"external_directory": {TEMPLATE_READ: "deny"}}
    return routing_text(config)


def _write(path, text):
    with open(path, "w", encoding="utf-8", newline="") as handle:
        handle.write(text)


def load_agent_text(repo_root, role):
    """Read agents/<role>.md as it is on disk, line endings included."""
    _check_role(role)
    path = Path(repo_root) / "agents" / f"{role}.md"
    try:
        return path.read_bytes().decode("utf-8")
    except (OSError, ValueError) as error:
        raise AdapterError(f"{path.as_posix()} cannot be read: {error}") from error


_EOLS = "\r\n"
DENY_ALL = '    "*": deny'


def _eol(line):
    return line[len(line.rstrip(_EOLS)):]


def _deny_bash_default(lines, end):
    """The catch-all entry that opens the bash map becomes a deny, when there is exactly one."""
    found = [
        index
        for index in range(2, end)
        if lines[index].rstrip(_EOLS) == '    "*": ask' and lines[index - 1].rstrip(_EOLS) == "  bash:"
    ]
    if len(found) == 1:
        lines[found[0]] = DENY_ALL + _eol(lines[found[0]])


def _deny_external_directory(lines, end):
    """A catch-all deny comes first in the external_directory map, or opens a new map under permission:."""
    maps = [index for index in range(1, end) if lines[index].startswith("  external_directory:")]
    permission = _top_level(lines, end, "permission")
    if len(maps) == 1 and lines[maps[0]].rstrip(_EOLS) == "  external_directory:":
        lines.insert(maps[0] + 1, DENY_ALL + _eol(lines[maps[0]]))
    elif not maps and len(permission) == 1 and lines[permission[0]].rstrip(_EOLS) == "permission:":
        eol = _eol(lines[permission[0]])
        lines[permission[0] + 1:permission[0] + 1] = ["  external_directory:" + eol, DENY_ALL + eol]


def deny_unanswerable_asks(text):
    """The agent file for a headless run: an ask that nobody can answer ends the run without a reply (F13, F78).

    In the per-run copy only, the bash catch-all ask becomes a deny and external_directory gets a catch-all
    deny before its allows, so an unlisted command or path is an error the agent can work around. Every other
    rule keeps its place and the line endings are kept. A file without the expected lines is returned unchanged.
    """
    lines = text.splitlines(keepends=True)
    end = _frontmatter_end(lines)
    _deny_bash_default(lines, end)
    _deny_external_directory(lines, end)
    return "".join(lines)


def prepare_run_dir(directory, role, agent_text, model, effort=None):
    """Write the per-run files under directory and return where OpenCode finds them.

    Nothing is written unless the role, the agent text and the model are valid.
    """
    _check_role(role)
    derived = deny_unanswerable_asks(derive_agent(agent_text))
    routing = render_run_config({role: model}, {role: effort} if effort else None, headless=True)
    root = Path(directory)
    config_dir = root / "opencode-config"
    (config_dir / "agents").mkdir(parents=True, exist_ok=True)
    _write(config_dir / "agents" / f"{role}.md", derived)
    config_file = root / "run-routing.json"
    _write(config_file, routing)
    return RunSetup(config_file=config_file, config_dir=config_dir)


SESSION_ID = re.compile(r"ses_[A-Za-z0-9]+")


def build_export_command(executable, session_id):
    """The command that exports a session: its assistant message says which agent and model ran (F43)."""
    if not isinstance(session_id, str) or not SESSION_ID.fullmatch(session_id):
        raise AdapterError(f"session id {session_id!r} is not an OpenCode session id")
    return [str(executable), "export", session_id]
