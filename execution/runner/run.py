"""Run one review through OpenCode and record it (Phase 2, plan steps 2.1 and 2.2).

run_review joins the pieces: it resolves the role to its model (the policy is
checked), writes a per-run config folder with a primary copy of the agent,
starts OpenCode in the target repo, and reads the events. The session is
exported only when the events look clean (about 5 s, F44), because the export
says which agent and model really ran (F34, F43). Then the report is checked
(artifact level) and the RunRecord is built. The workflow level stays not_run
until the gates exist (Phase 3A).

Nothing is written into the target repo, and the per-run folder is deleted
afterwards. Appending the record is a separate call (record.append_record), so
a test or a dry run writes nothing. The subprocess runner is injectable, so the
tests replay recorded OpenCode output. A policy rejection, a failed preflight, a
missing diff and a missing opencode raise, because nothing ran; every other
failure is a record.
"""

import os
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

from . import opencode_adapter as adapter
from . import preflight, record, report, resolve
from lib.opencode_resolved import find_opencode  # noqa: E402

RUNTIME = "opencode"
RUN_TIMEOUT = 600
EXPORT_TIMEOUT = 120
# One plain line (F10). It states the branch decision and the approval, which the
# global AGENTS.md gates would otherwise ask for in a headless run (F8).
TASK_MESSAGE = (
    "Review the attached diff. Your whole reply must be only the JSON object that the attached task file "
    "describes, with no text before or after it, even if your instructions describe another output format. "
    "Do not create a branch and do not ask to confirm a plan: the plan is approved."
)


@dataclass(frozen=True)
class Outcome:
    record: dict
    report: dict | None


@dataclass(frozen=True)
class Launched:
    returncode: int
    stdout: str
    stderr: str
    note: str | None


def _text(value):
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value or ""


def _launch(runner, command, cwd, environment, timeout):
    """Run one command. A timeout or a failed start becomes a note, not an exception."""
    try:
        done = runner(
            command,
            cwd=str(cwd),
            env=environment,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as error:
        return Launched(-1, _text(error.stdout), _text(error.stderr), f"OpenCode did not finish within {timeout} s")
    except OSError as error:
        return Launched(-1, "", "", f"OpenCode could not start: {error}")
    return Launched(done.returncode, _text(done.stdout), _text(done.stderr), None)


def _export(runner, executable, session_id, cwd, environment):
    """The agent and model that ran, read from the session export: (RanInfo or None, note or None)."""
    try:
        command = adapter.build_export_command(executable, session_id)
    except adapter.AdapterError as error:
        return None, str(error)
    done = _launch(runner, command, cwd, environment, EXPORT_TIMEOUT)
    if done.note or done.returncode != 0:
        return None, done.note or f"opencode export exited with code {done.returncode}"
    try:
        return adapter.parse_export(done.stdout), None
    except adapter.AdapterError as error:
        return None, str(error)


def _events_look_clean(events, launched, resolved):
    """True when only the model that ran is left to check.

    A RanInfo that matches the request stands in for the export, so every
    problem that is left comes from the events, the exit code or stderr.
    """
    stand_in = adapter.RanInfo(agent=resolved.role, model=resolved.model, finish="stop")
    result = adapter.assess(events, launched.stderr, stand_in, resolved.role, resolved.model, launched.returncode)
    return not result.problems


def _artifact_level(assessment):
    """(status, report, problems) of the artifact level; not_run when the run itself failed."""
    if assessment.status != "success":
        return "not_run", None, ()
    check = report.parse_report(assessment.reply)
    return check.status, check.report, check.problems


def _record(resolved, diff, assessment, artifact, messages, launched, duration_ms):
    status = record.status_levels(assessment.status, artifact)
    failed = "failure" in status.values()
    error = None
    if failed:
        error = record.error_info("; ".join(messages), launched.stderr, launched.stdout.splitlines(), assessment.reply)
    return record.build_record(
        role=resolved.role,
        profile=resolved.profile,
        runtime=RUNTIME,
        requested_model=resolved.model,
        resolved_model=assessment.resolved_model,
        policy_result="pass",
        fallback=assessment.fallback,
        input_artifacts=[diff.name],
        output_artifacts=[],
        status=status,
        stop_reason=assessment.stop_reason,
        tokens=assessment.tokens,
        cost=assessment.cost,
        duration_ms=duration_ms,
        verification=None,
        error=error,
    )


def _run(work, resolved, executable, agent_text, diff, target, runner, timeout, base):
    role, model = resolved.role, resolved.model
    setup = adapter.prepare_run_dir(work, role, agent_text, model)
    task_file = work / "task.md"
    task_file.write_text(report.task_message(), encoding="utf-8", newline="\n")
    command = adapter.build_command(executable, role, TASK_MESSAGE, [task_file, diff])
    environment = adapter.build_environment(base, setup.config_file, setup.config_dir)
    started = time.monotonic()
    launched = _launch(runner, command, target, environment, timeout)
    events = adapter.parse_events(launched.stdout)
    ran = None
    notes = [launched.note] if launched.note else []
    if not launched.note and _events_look_clean(events, launched, resolved):
        ran, export_note = _export(runner, executable, events.session_id, target, base)
        notes += [export_note] if export_note else []
    assessment = adapter.assess(events, launched.stderr, ran, role, model, launched.returncode)
    artifact, checked, problems = _artifact_level(assessment)
    messages = notes + list(assessment.problems) + list(problems)
    duration_ms = int((time.monotonic() - started) * 1000)
    built = _record(resolved, diff, assessment, artifact, messages, launched, duration_ms)
    return Outcome(record=built, report=checked)


def run_review(
    repo_root,
    target,
    role,
    diff_file,
    profile_name="default",
    timeout=RUN_TIMEOUT,
    runner=subprocess.run,
    environ=None,
    which=shutil.which,
):
    """Run the role's agent on the diff in the target repo and return the Outcome."""
    resolved = resolve.resolve(role, repo_root, profile_name)
    executable = find_opencode(which)
    agent_text = adapter.load_agent_text(repo_root, role)
    diff = Path(diff_file).resolve()
    if not diff.is_file():
        raise adapter.AdapterError(f"{diff.as_posix()} not found, so there is nothing to review")
    base = dict(os.environ if environ is None else environ)
    preflight.require(target, role, base)
    work = Path(tempfile.mkdtemp(prefix="review-run-"))
    try:
        return _run(work, resolved, executable, agent_text, diff, Path(target), runner, timeout, base)
    finally:
        shutil.rmtree(work, ignore_errors=True)
