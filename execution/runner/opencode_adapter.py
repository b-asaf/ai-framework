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

Everything here is a pure function. Running OpenCode is a later slice. The
sample files in tests/fixtures/opencode-run/ come from real runs.
"""

import json
import re
from dataclasses import dataclass

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


def parse_export(text):
    """Read the agent and the model that ran from the last assistant message of `opencode export`."""
    infos = _assistant_infos(_load_export(text))
    if not infos:
        raise AdapterError("the session export has no assistant message, so the model that ran is unknown")
    info = infos[-1]
    return RanInfo(agent=info.get("agent"), model=_model_id(info), finish=info.get("finish"))


def check_model_ran(ran, agent, model):
    """Return one message per difference between what ran and what was requested."""
    problems = []
    if ran.agent != agent:
        problems.append(f"the run used agent '{ran.agent}', not '{agent}': OpenCode fell back to another agent (F6)")
    if ran.model != model:
        problems.append(f"the run used model '{ran.model}', not the requested '{model}' (F34)")
    return problems


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


def assess(events, stderr, ran, agent, model, exit_code=0):
    """The execution level of a run: success only when nothing above went wrong.

    A fallback, a model mismatch and a non-zero exit code count as failures. The
    result keeps the model that really ran, so the record shows why. ran is None
    when the session export was not read, as after a run that failed before any
    reply; a run that looks fine otherwise but has no export fails closed (F34).
    """
    warnings = fallback_warnings(stderr)
    problems = _event_problems(events)
    if exit_code != 0:
        problems.append(f"OpenCode exited with code {exit_code}")
    problems += [f"stderr: {warning}" for warning in warnings]
    if ran is not None:
        problems += check_model_ran(ran, agent, model)
    elif not problems:
        problems.append("the session export was not read, so the model that ran is unknown (F34)")
    return Assessment(
        status="failure" if problems else "success",
        problems=tuple(problems),
        fallback=_fell_back(warnings, ran, agent),
        resolved_model=ran.model if ran else None,
        stop_reason=events.reason,
        tokens=events.tokens,
        cost=events.cost,
        reply=events.reply,
    )
