r"""Strict checks for agent frontmatter.

The validator's hand-rolled parser accepts anything it can split on a colon.
A standards-following YAML parser is stricter, so a file the validator accepts
can still be rejected or misread by the tools that load it. This module adds
the checks the hand-rolled parser lacks.

Rule 1: inside a double-quoted string the only allowed escapes are \\, \" and
\/. Windows paths belong in single quotes, where backslashes stay literal, or
need every backslash doubled.

A quote starts a string only at the start of a line or right after a colon, so
an apostrophe inside a plain value (it's) never opens one. Text after " #" is
a comment.
"""

ALLOWED_ESCAPES = ("\\", '"', "/")


def _frontmatter_lines(text):
    lines = text.lstrip("\ufeff").splitlines()
    if not lines or lines[0].strip() != "---":
        return
    for number, line in enumerate(lines[1:], start=2):
        if line.strip() == "---":
            return
        yield number, line


def _bad_escapes(line):
    found = []
    in_string = None  # None, "'" or '"'
    previous = ""  # last non-space character seen outside a string
    i = 0
    while i < len(line):
        char = line[i]
        if in_string is None:
            if char == "#" and (i == 0 or line[i - 1] in " \t"):
                break
            if char in ("'", '"') and previous in ("", ":"):
                in_string = char
            elif not char.isspace():
                previous = char
        elif in_string == '"':
            if char == "\\":
                following = line[i + 1] if i + 1 < len(line) else ""
                if following not in ALLOWED_ESCAPES:
                    found.append("\\" + following)
                i += 1
            elif char == '"':
                in_string = None
                previous = char
        elif char == "'":
            if line[i + 1 : i + 2] == "'":
                i += 1
            else:
                in_string = None
                previous = char
        i += 1
    return found


def lint_frontmatter(text):
    """Return (line_number, message) for each problem; line numbers are file lines."""
    issues = []
    for number, line in _frontmatter_lines(text):
        bad = list(dict.fromkeys(_bad_escapes(line)))
        if bad:
            issues.append(
                (
                    number,
                    "unsafe escape sequence(s) in a double-quoted string: "
                    + ", ".join(bad)
                    + ". Use single quotes (backslashes stay literal) or double each backslash.",
                )
            )
    return issues
