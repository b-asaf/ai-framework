"""RunRecord builder and store (Phase 2, plan steps 2.1 and 2.2, sections 5.3 and 5.4).

A RunRecord answers why a model actually ran. Its shape is the contract in
execution/schemas/run-record.schema.json, checked by contract.py. This module
adds the rules a schema cannot express, builds records, and appends them as one
JSON line each to execution/runner/runs/<date>.jsonl. A record is validated
before anything is written (fail closed, DEC-015). Nothing here knows about a
runtime (plan section 5.7).
"""

import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

from . import contract

DEFAULT_RUNS_DIR = Path(__file__).resolve().parent / "runs"
LEVELS = ("execution", "artifact", "workflow")
TIMESTAMP = re.compile(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ")
TAIL_LINES = 20
LINE_CHARS = 500
REPLY_CHARS = 1500


class RecordError(Exception):
    """A run record is not valid."""


def status_levels(execution="not_run", artifact="not_run", workflow="not_run"):
    """The per-level status object of a RunRecord."""
    return {"execution": execution, "artifact": artifact, "workflow": workflow}


def _tail(lines):
    return [line[:LINE_CHARS] for line in lines[-TAIL_LINES:]]


def error_info(message, stderr="", events=(), reply=None):
    """The error object of a failed run: the message, the last lines of stderr and of the events,
    and the start of the reply when there is one (what a failed report check saw)."""
    info = {
        "message": message,
        "stderr_tail": "\n".join(_tail(str(stderr).splitlines())),
        "event_tail": _tail([str(event) for event in events]),
    }
    if reply:
        info["reply_head"] = str(reply)[:REPLY_CHARS]
    return info


def _check_levels(status):
    return [
        f"{level} cannot succeed unless {previous} succeeded"
        for previous, level in zip(LEVELS, LEVELS[1:])
        if status[level] == "success" and status[previous] != "success"
    ]


def _check_rules(record):
    problems = []
    if not TIMESTAMP.fullmatch(record["timestamp"]):
        problems.append("timestamp must look like 2026-10-21T10:00:00Z (UTC)")
    problems += _check_levels(record["status"])
    if "failure" in record["status"].values() and not record["error"]:
        problems.append("a failed level needs an error object")
    return problems


def check_record(record):
    """Return one message per problem; an empty list means a valid record.

    Schema problems come first and stop the rules. A missing schema raises ContractError.
    """
    return contract.validate_contract(record, "run-record") or _check_rules(record)


def _raise_if_invalid(record):
    problems = check_record(record)
    if problems:
        raise RecordError("; ".join(problems))


def utc_now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_record(run_id=None, timestamp=None, **fields):
    """Fill run_id and timestamp when missing, validate, and return the record."""
    record = dict(fields, run_id=run_id or uuid.uuid4().hex, timestamp=timestamp or utc_now())
    _raise_if_invalid(record)
    return record


def to_jsonl(record):
    """One line of JSON, keys sorted, no newline inside."""
    return json.dumps(record, sort_keys=True)


def append_record(record, runs_dir=None):
    """Validate the record, then append it to <runs_dir>/<date>.jsonl and return that path."""
    _raise_if_invalid(record)
    directory = Path(runs_dir) if runs_dir is not None else DEFAULT_RUNS_DIR
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{record['timestamp'][:10]}.jsonl"
    with open(path, "a", encoding="utf-8", newline="\n") as handle:
        handle.write(to_jsonl(record) + "\n")
    return path
