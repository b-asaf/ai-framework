"""Resolved model of an agent through `opencode debug agent <name>` (step 1b.4 e, DEC-019).

`debug agent` prints the agent as OpenCode resolves it, without a model call.
This is the only place that knows its output format. The check is opt-in
(--resolved-models) and fails closed: when the output cannot be read, the
caller reports a problem instead of passing.

Note: OpenCode reads agents through the linked global config (F17), so this
compares the installed agents with the profile, not the files of a worktree.
"""

import re
import shutil
import subprocess

_MODEL_BLOCK = re.compile(r'^  "model": \{([^{}]*)\}', re.MULTILINE)
_PROVIDER = re.compile(r'"providerID":\s*"([^"]+)"')
_MODEL = re.compile(r'"modelID":\s*"([^"]+)"')


class ResolvedModelError(Exception):
    """The resolved model of an agent could not be read."""


def parse_resolved_model(output):
    """Return 'provider/model' from the top-level model block, or None when the agent has no model."""
    block = _MODEL_BLOCK.search(output)
    if block is None:
        return None
    provider = _PROVIDER.search(block.group(1))
    model = _MODEL.search(block.group(1))
    if provider is None or model is None:
        return None
    return f"{provider.group(1)}/{model.group(1)}"


def find_opencode(which=shutil.which):
    executable = which("opencode")
    if executable is None:
        raise ResolvedModelError("`opencode` was not found on PATH, so resolved models cannot be read")
    return executable


def fetch_resolved_model(executable, name, runner=subprocess.run, timeout=60):
    try:
        result = runner(
            [executable, "debug", "agent", name],
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise ResolvedModelError(f"`opencode debug agent {name}` could not run: {error}") from error
    if result.returncode != 0:
        detail = (result.stderr or "").strip()[-300:]
        raise ResolvedModelError(f"`opencode debug agent {name}` exited with {result.returncode}: {detail}")
    return parse_resolved_model((result.stdout or "") + "\n" + (result.stderr or ""))
