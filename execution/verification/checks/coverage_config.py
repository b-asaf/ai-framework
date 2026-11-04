"""Coverage-minimum setting (DEC-015 point 3).

`.ai-framework.json` may hold {"coverage": {"minChangedLines": N}}: the minimum percentage of
changed lines the tests must cover. `code-reviewer` Stage 2 applies it (the thresholds table in
skills/static-code-analysis/SKILL.md is the one place that states the default). This module only
validates the setting, so a typo blocks the push instead of silently turning the check into the
default or off. Absent means the default of 90; 0 means no minimum.
"""

DEFAULT_MIN_CHANGED_LINES = 90


class CoverageConfigError(Exception):
    """coverage.minChangedLines is present but is not a whole number from 0 to 100."""


def read_minimum(config=None):
    """Return the configured minimum (0 to 100), or the default when the setting is absent."""
    if config is None:
        config = {}
    if not isinstance(config, dict):
        raise CoverageConfigError(f"config must be a dict or None, got {type(config)!r}")
    coverage = config.get("coverage", {})
    if not isinstance(coverage, dict):
        raise CoverageConfigError("coverage in .ai-framework.json must be an object")
    value = coverage.get("minChangedLines")
    if value is None:
        return DEFAULT_MIN_CHANGED_LINES
    if not isinstance(value, int) or isinstance(value, bool) or not 0 <= value <= 100:
        raise CoverageConfigError(
            "coverage.minChangedLines in .ai-framework.json must be a whole number from 0 to 100"
        )
    return value
