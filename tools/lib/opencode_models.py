"""Live model discovery through `opencode models`.

This is the only place that knows how OpenCode lists models. The check is
opt-in (--live-models) and fails closed: when the live list cannot be read, the
caller reports a problem instead of passing.
"""

import shutil
import subprocess


class LiveModelError(Exception):
    """The live model list could not be read."""


def parse_models(output):
    """Keep lines that look like provider/model ids (a slash, no spaces)."""
    models = set()
    for line in output.splitlines():
        candidate = line.strip()
        if "/" in candidate and not any(char.isspace() for char in candidate):
            models.add(candidate)
    return models


def fetch_live_models(runner=subprocess.run, which=shutil.which, timeout=60):
    executable = which("opencode")
    if executable is None:
        raise LiveModelError(
            "`opencode` was not found on PATH, so the live model list cannot be read"
        )
    try:
        result = runner(
            [executable, "models"],
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise LiveModelError(f"`opencode models` could not run: {error}") from error
    if result.returncode != 0:
        detail = (result.stderr or "").strip()[-300:]
        raise LiveModelError(f"`opencode models` exited with {result.returncode}: {detail}")
    models = parse_models(result.stdout)
    if not models:
        raise LiveModelError("`opencode models` returned no model ids")
    return models


def find_unknown_models(agent_models, live_models):
    """Return sorted (agent_name, model) pairs whose model is not live."""
    return sorted(
        (name, model) for name, model in agent_models.items() if model not in live_models
    )
