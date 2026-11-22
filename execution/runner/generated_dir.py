"""The folder for the files the framework generates in a project (DEC-026, plan step S.12b).

The folder is `.ai-framework/` at the repository root, or the relative path in the `generatedDir` key of the
project's `.ai-framework.json`. Everything is decided here and fails closed (DEC-015, point 3): a value that is
not a plain relative path inside the repository raises GeneratedDirError, and there is no fallback to another
place. A missing `.ai-framework.json` gives the default (the runner preflight reports the missing file by
itself); a file that cannot be read gives an error. check_value is pure; the other functions read the target.
"""

import json
from pathlib import Path

CONFIG_NAME = ".ai-framework.json"
KEY = "generatedDir"
DEFAULT_DIR = ".ai-framework"


class GeneratedDirError(Exception):
    """The folder for generated files cannot be decided."""


def _problem(value, why):
    return GeneratedDirError(f"{KEY} {value!r} in {CONFIG_NAME} {why}")


def _check_text(value):
    if not isinstance(value, str):
        raise _problem(value, "must be a string")
    if not value.strip() or value == ".":
        raise _problem(value, "must name a folder, not be empty or '.'")
    if value != value.strip() or any(ord(char) < 32 or ord(char) == 127 for char in value):
        raise _problem(value, "must not start or end with whitespace or hold a control character")


def _check_absolute(value):
    if value[0] in "/\\" or value[1:2] == ":":
        raise _problem(value, "must be relative to the repository, not absolute")
    if "\\" in value:
        raise _problem(value, "must be written with forward slashes")
    if ":" in value:
        raise _problem(value, "must not contain ':'")


def _check_chars(value):
    if not all(char.isalnum() or char in "._-/ " for char in value):
        raise _problem(value, "may hold only letters, digits, spaces and . _ - /")


def _check_segments(value):
    for segment in value.split("/"):
        if not segment:
            raise _problem(value, "has an empty segment (a doubled or trailing slash)")
        if segment in (".", ".."):
            raise _problem(value, "must not have a '.' or '..' segment")
        if segment.lower() == ".git":
            raise _problem(value, "must not use a '.git' folder")


def check_value(value):
    """The folder as a relative path with forward slashes, or GeneratedDirError. Pure: no file is read."""
    _check_text(value)
    _check_absolute(value)
    _check_chars(value)
    _check_segments(value)
    return value


def read_key(target):
    """The generatedDir value of the target's .ai-framework.json, or the default when the file or the key is absent."""
    path = Path(target) / CONFIG_NAME
    if not path.is_file():
        return DEFAULT_DIR
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as error:
        raise GeneratedDirError(f"{CONFIG_NAME} cannot be read: {error}") from error
    if not isinstance(data, dict):
        raise GeneratedDirError(f"{CONFIG_NAME} must be a JSON object")
    return data[KEY] if KEY in data else DEFAULT_DIR


def _inside(target, relative):
    root = Path(target).resolve()
    folder = (root / relative).resolve()
    if folder == root or not folder.is_relative_to(root):
        raise GeneratedDirError(
            f"the generated-files folder {relative!r} does not resolve to a folder inside the repository "
            f"(it leads to {folder.as_posix()})"
        )


def relative_dir(target):
    """The folder relative to the target, with forward slashes, or GeneratedDirError."""
    relative = check_value(read_key(target))
    _inside(target, relative)
    return relative


def absolute_dir(target):
    """The folder as a path under the target (links are not resolved in the result), or GeneratedDirError."""
    return Path(target) / relative_dir(target)
