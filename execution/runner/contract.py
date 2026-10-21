"""Contract checks for runner artifacts (Phase 2, plan section 5.2).

execution/schemas/*.schema.json are the contracts between stages. This module
is the one checker for them: a small, stdlib-only subset of JSON Schema (the
repo has no dependencies to install). A schema that uses a keyword this
checker does not enforce is rejected, so a contract can never look stricter
than it is (fail closed, DEC-015). Everything here is a pure function except
load_schema, which reads a file.
"""

import json
from pathlib import Path

SCHEMA_DIR = Path(__file__).resolve().parent.parent / "schemas"

TYPES = {
    "object": lambda value: isinstance(value, dict),
    "array": lambda value: isinstance(value, list),
    "string": lambda value: isinstance(value, str),
    "integer": lambda value: isinstance(value, int) and not isinstance(value, bool),
    "number": lambda value: isinstance(value, (int, float)) and not isinstance(value, bool),
    "boolean": lambda value: isinstance(value, bool),
    "null": lambda value: value is None,
}
KEYWORDS = {"type", "enum", "required", "properties", "additionalProperties", "items", "minLength", "minimum"}
ANNOTATIONS = {"title", "description"}


class ContractError(Exception):
    """A schema is missing, unreadable, or uses something this checker does not enforce."""


def _type_names(schema):
    declared = schema.get("type")
    if declared is None:
        return []
    return declared if isinstance(declared, list) else [declared]


def _kind(value):
    return next((name for name, test in TYPES.items() if test(value)), type(value).__name__)


def check_schema(schema, where="schema"):
    """Raise ContractError unless every keyword in the schema is one this checker enforces."""
    if not isinstance(schema, dict):
        raise ContractError(f"{where} must be an object")
    unknown = sorted(set(schema) - KEYWORDS - ANNOTATIONS)
    if unknown:
        raise ContractError(f"{where} uses unsupported keyword(s): {', '.join(unknown)}")
    bad_types = [name for name in _type_names(schema) if name not in TYPES]
    if bad_types:
        raise ContractError(f"{where} names unknown type(s): {', '.join(bad_types)}")
    if not isinstance(schema.get("additionalProperties", True), bool):
        raise ContractError(f"{where}: additionalProperties must be true or false")
    for name, sub_schema in schema.get("properties", {}).items():
        check_schema(sub_schema, f"{where}.properties.{name}")
    if "items" in schema:
        check_schema(schema["items"], f"{where}.items")


def load_schema(name):
    """Read execution/schemas/<name>.schema.json and make sure the checker can enforce all of it."""
    path = SCHEMA_DIR / f"{name}.schema.json"
    if not path.is_file():
        raise ContractError(f"{path.as_posix()} not found, so the contract cannot be checked")
    try:
        schema = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as error:
        raise ContractError(f"{path.name} cannot be read: {error}") from error
    check_schema(schema, path.name)
    return schema


def _check_type(value, schema, where):
    names = _type_names(schema)
    if names and not any(TYPES[name](value) for name in names):
        return [f"{where}: expected {' or '.join(names)}, got {_kind(value)}"]
    return []


def _check_enum(value, schema, where):
    allowed = schema.get("enum")
    if allowed is not None and value not in allowed:
        return [f"{where}: {value!r} is not one of {allowed}"]
    return []


def _check_bounds(value, schema, where):
    problems = []
    if isinstance(value, str) and len(value) < schema.get("minLength", 0):
        problems.append(f"{where}: shorter than {schema['minLength']} characters")
    if TYPES["number"](value) and value < schema.get("minimum", value):
        problems.append(f"{where}: {value} is below {schema['minimum']}")
    return problems


def _check_object(value, schema, where):
    if not isinstance(value, dict):
        return []
    problems = [f"{where}: missing '{name}'" for name in schema.get("required", []) if name not in value]
    known = schema.get("properties", {})
    for name, item in value.items():
        if name in known:
            problems += _check_node(item, known[name], f"{where}.{name}")
        elif schema.get("additionalProperties") is False:
            problems.append(f"{where}: unexpected '{name}'")
    return problems


def _check_array(value, schema, where):
    item_schema = schema.get("items")
    if not isinstance(value, list) or item_schema is None:
        return []
    problems = []
    for index, item in enumerate(value):
        problems += _check_node(item, item_schema, f"{where}[{index}]")
    return problems


def _check_node(value, schema, where):
    problems = _check_type(value, schema, where)
    if problems:
        return problems
    problems = _check_enum(value, schema, where) + _check_bounds(value, schema, where)
    return problems + _check_object(value, schema, where) + _check_array(value, schema, where)


def validate(instance, schema):
    """Return one message per way the instance breaks the schema; an empty list means valid."""
    return _check_node(instance, schema, "$")


def validate_contract(instance, name):
    """Validate an instance against execution/schemas/<name>.schema.json."""
    return validate(instance, load_schema(name))
