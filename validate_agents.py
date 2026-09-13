#!/usr/bin/env python3
"""Deterministic validation for ai-framework's agents/ directory.

Covers item 6 from the ai-framework handoff:
  - every agent's assigned model exists in the model catalog
  - delegation edges between agents that cross model families are
    reported, so drift from the intended family mix is visible
  - every agent's `mode:` matches how it is actually invoked
    (primary = entry point, subagent = only reached via Task)
  - any `deny` rule a DEC has marked as required is actually present

Conventions this script depends on (see README section at the bottom of
this file if these don't match the real repo yet):
  - agent frontmatter is a simple indentation-based key: value block
    between `---` fences, with `mode:`, `model:`, and an optional
    `permission.task` mapping of subagent-name -> allow|deny.
  - the model catalog is a JSON file mapping model id -> either a family
    string or an object with a `family` key.
  - a DEC file can require a specific deny rule by including an HTML
  - a DEC file can require a specific deny rule by including an HTML
    comment directive, with the permission path quoted since command
    patterns can contain spaces/asterisks:
    <!-- requires-deny: agent=X permission="task.Y" -->
    <!-- requires-deny: agent=X permission="bash.some command *" -->
    The path's first segment is the top-level permission category
    (task, bash, edit, write, external_directory, ...); everything after
    the first "." is looked up as a literal key in that category's dict.

No third-party dependencies: frontmatter parsing is hand-rolled rather
than using PyYAML, since the frontmatter shape this script needs
(flat keys plus one level of nesting) doesn't need a full YAML parser.
It will NOT handle lists, multi-line strings, anchors, or arbitrary
nesting depth — if the real frontmatter needs any of that, this parser
should be swapped for PyYAML rather than extended ad hoc.

Exit code is 0 only if every check passes, so this is safe to wire
directly into `setup.py --verify`.
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

FRONTMATTER_PATTERN = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)
REQUIRES_DENY_PATTERN = re.compile(
    r'<!--\s*requires-deny:\s*agent=(?P<agent>[\w-]+)\s+'
    r'permission="(?P<permission>[^"]+)"\s*-->'
)

VALID_MODES = {"primary", "subagent"}


@dataclass
class Issue:
    """A single validation failure, tied to the file that caused it."""

    file: str
    check: str
    message: str

    def __str__(self) -> str:
        return f"[{self.check}] {self.file}: {self.message}"


@dataclass
class Agent:
    """Parsed view of one agents/*.md file, enough to run every check."""

    path: Path
    mode: str | None
    model: str | None
    permission: dict
    task_permissions: dict[str, str]

    @property
    def name(self) -> str:
        return self.path.stem

    def permission_value(self, dotted_path: str) -> str | None:
        """Look up e.g. "bash.lizard *" or "task.general" in this agent's
        permission block. The category (segment before the first ".") is a
        top-level permission key (task, bash, edit, write,
        external_directory, ...); everything after is a literal key in
        that category's dict — not a further dotted path, since command
        patterns themselves can legitimately contain dots (file paths)."""
        category, separator, pattern = dotted_path.partition(".")
        if not separator:
            return None
        category_block = self.permission.get(category)
        if not isinstance(category_block, dict):
            return None
        return category_block.get(pattern)


def strip_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


def split_key_value(line: str) -> tuple[str, str]:
    """Split one frontmatter line into (key, raw_value).

    Quote-aware: a key like 'powershell -File "$env:USERPROFILE\\..."' or
    "D:\\ai-framework\\skills\\...\\*" contains a literal colon inside its
    quotes, so the split point can't just be "the first colon in the
    line" — it has to be "the first colon after the matching closing
    quote," when the line starts with a quote at all.
    """
    stripped = line.strip()
    if stripped[:1] in ("'", '"'):
        quote_char = stripped[0]
        closing_index = stripped.index(quote_char, 1)
        key = stripped[1:closing_index]
        remainder = stripped[closing_index + 1 :].lstrip()
        if not remainder.startswith(":"):
            raise ValueError(f"expected ':' after quoted key in: {line!r}")
        value = remainder[1:].strip()
    else:
        key, separator, value = stripped.partition(":")
        if not separator:
            raise ValueError(f"cannot parse frontmatter line: {line!r}")
        key, value = key.strip(), value.strip()
    return key, value


def parse_simple_yaml(text: str) -> dict:
    """Parse an indentation-based `key: value` mapping into a nested dict.

    Handles arbitrary nesting depth (frontmatter here goes three levels:
    permission -> bash -> individual command patterns) and quoted keys
    containing colons. Does NOT handle YAML lists, multi-line strings, or
    anchors — none of those appear in agent frontmatter today; if that
    changes, swap this for PyYAML rather than extending it ad hoc.
    """
    root: dict = {}
    stack: list[tuple[int, dict]] = [(-1, root)]

    for raw_line in text.splitlines():
        if not raw_line.strip() or raw_line.strip().startswith("#"):
            continue
        indent = len(raw_line) - len(raw_line.lstrip(" "))
        key, value = split_key_value(raw_line)
        key = strip_quotes(key)

        while indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1]

        if value == "{}":
            parent[key] = {}
        elif value == "":
            child: dict = {}
            parent[key] = child
            stack.append((indent, child))
        else:
            parent[key] = strip_quotes(value)

    return root


def parse_frontmatter(path: Path) -> dict:
    """Extract and parse the frontmatter block from an agent file."""
    text = path.read_text(encoding="utf-8-sig")
    match = FRONTMATTER_PATTERN.match(text)
    if not match:
        raise ValueError(f"{path} has no frontmatter block")
    return parse_simple_yaml(match.group(1))


def load_agent(path: Path) -> Agent:
    frontmatter = parse_frontmatter(path)
    permission = frontmatter.get("permission") or {}
    task_permissions = permission.get("task") or {}
    return Agent(
        path=path,
        mode=frontmatter.get("mode"),
        model=frontmatter.get("model"),
        permission=permission,
        task_permissions=task_permissions,
    )


def discover_agents(agents_dir: Path) -> list[Agent]:
    paths = sorted(agents_dir.glob("*.md"))
    if not paths:
        raise FileNotFoundError(f"no agent files found under {agents_dir}")
    return [load_agent(path) for path in paths]


def _split_markdown_row(line: str) -> list[str]:
    cells = line.strip().strip("|").split("|")
    return [strip_quotes(c.strip().strip("`")) for c in cells]


def _is_separator_row(cells: list[str]) -> bool:
    """A markdown table's header-divider row, e.g. `| --- | :--: |`."""
    return all(re.fullmatch(r":?-+:?", c) for c in cells if c)


def _find_column(headers: list[str], *candidates: str) -> int | None:
    """Index of the first header cell containing any candidate substring."""
    lowered = [h.lower() for h in headers]
    for candidate in candidates:
        for i, header in enumerate(lowered):
            if candidate in header:
                return i
    return None


def _parse_markdown_tables(text: str) -> list[list[list[str]]]:
    """Split a markdown document into tables, each a list of row-cell-lists."""
    tables: list[list[list[str]]] = []
    current: list[list[str]] = []
    for line in text.splitlines():
        if line.strip().startswith("|"):
            current.append(_split_markdown_row(line))
        elif current:
            tables.append(current)
            current = []
    if current:
        tables.append(current)
    return tables


def load_model_catalog_from_markdown(catalog_path: Path) -> dict[str, str]:
    """Return model id -> family, read from a markdown table.

    Scans every table in the file for one whose header row has both a
    "model" column and a "family"/"provider" column, and uses the first
    such table found. If no table matches, raises with the headers it did
    see, since guessing wrong here would silently validate against an
    empty or bogus catalog.
    """
    text = catalog_path.read_text(encoding="utf-8-sig")
    tables = _parse_markdown_tables(text)

    seen_headers: list[list[str]] = []
    for table in tables:
        if len(table) < 2:
            continue
        header, *rows = table
        if rows and _is_separator_row(rows[0]):
            rows = rows[1:]

        model_col = _find_column(header, "model")
        family_col = _find_column(header, "family", "provider")
        if model_col is None or family_col is None:
            seen_headers.append(header)
            continue

        catalog: dict[str, str] = {}
        for row in rows:
            if len(row) <= max(model_col, family_col) or _is_separator_row(row):
                continue
            model_id = row[model_col]
            family = row[family_col] or model_id.split("/")[0]
            if model_id:
                catalog[model_id] = family
        if catalog:
            return catalog

    raise ValueError(
        f"no table in {catalog_path} had both a 'model' column and a "
        f"'family'/'provider' column. Headers found: {seen_headers or 'none'}"
    )


def load_model_catalog(catalog_path: Path) -> dict[str, str]:
    """Return model id -> family, from a JSON file or a markdown table."""
    if catalog_path.suffix == ".md":
        return load_model_catalog_from_markdown(catalog_path)

    data = json.loads(catalog_path.read_text(encoding="utf-8-sig"))
    catalog: dict[str, str] = {}
    for model_id, entry in data.items():
        if isinstance(entry, str):
            catalog[model_id] = entry
        elif isinstance(entry, dict) and "family" in entry:
            catalog[model_id] = entry["family"]
        else:
            catalog[model_id] = model_id.split("/")[0]
    return catalog


def validate_model_exists(agent: Agent, catalog: dict[str, str]) -> list[Issue]:
    if agent.model is None:
        return [Issue(agent.name, "model-exists", "no `model:` field set")]
    if agent.model not in catalog:
        return [Issue(agent.name, "model-exists", f"model '{agent.model}' not in catalog")]
    return []


MENTION_PATTERN = re.compile(r"@([a-zA-Z][a-zA-Z0-9_-]*)")
DELEGATION_SCAN_DIRS = ("agents", "commands", "skills")


def find_delegators_of(agent_name: str, all_agents: list[Agent]) -> list[Agent]:
    """Agents whose `permission.task` names this agent (any decision)."""
    return [a for a in all_agents if agent_name in a.task_permissions]


def is_named_via_permission(agent_name: str, all_agents: list[Agent]) -> bool:
    """Whether another agent's permission.task grants `allow` for this one."""
    return any(
        delegator.task_permissions.get(agent_name) == "allow"
        for delegator in find_delegators_of(agent_name, all_agents)
    )


FORWARD_DELEGATION_HEADER_PATTERN = re.compile(r"route\s+to", re.IGNORECASE)
BULLET_MENTION_PATTERN = re.compile(r"^[ \t]*[-*][ \t]+`@([a-zA-Z][a-zA-Z0-9_-]*)`")
SAME_LINE_ROUTE_PATTERN = r"route\s+to\s+`?@{name}\b"
PROXIMITY_WINDOW_LINES = 5


def _forward_delegated_names_in_text(text: str) -> set[str]:
    """Names this text forward-delegates to, via either accepted phrasing.

    Two real conventions observed in this repo:
      1. Same-line: "Route to `@name`" (also matches lowercase "route to",
         but NOT "route back to `@name`", since "back" breaks the
         contiguous route...to phrase).
      2. Bullet list: "- `@name` — description", but ONLY when it falls
         within PROXIMITY_WINDOW_LINES lines of a "route to" trigger
         phrase earlier in the same paragraph (reset by a blank line).
         Without this proximity requirement, a purely descriptive bullet
         like "- `@orchestrator` — confirm doc status before final
         handoff" (which names an agent without delegating to it) matches
         the same syntax as a genuine delegation bullet like
         "- `@db` — persistence layer changes" and can't be told apart.

    Known gap: a name mentioned ONLY inside a parenthetical comma list
    like "delegate to it by name (`@a`, `@b`, `@c`)" matches neither
    pattern. Every agent seen in such a list so far also has a separate
    "Route to `@name`" call site elsewhere, so this hasn't caused a false
    negative yet — but it's a real, undetected limitation.
    """
    names: set[str] = set()

    for match in re.finditer(r"@([a-zA-Z][a-zA-Z0-9_-]*)", text):
        name = match.group(1)
        line_start = text.rfind("\n", 0, match.start()) + 1
        preceding_on_line = text[line_start : match.start()]
        if FORWARD_DELEGATION_HEADER_PATTERN.search(preceding_on_line) and "back" not in preceding_on_line.lower():
            names.add(name)

    lines_since_route_header: int | None = None
    for line in text.splitlines():
        if not line.strip():
            lines_since_route_header = None
        elif FORWARD_DELEGATION_HEADER_PATTERN.search(line):
            lines_since_route_header = 0
        elif lines_since_route_header is not None:
            lines_since_route_header += 1

        if lines_since_route_header is not None and lines_since_route_header <= PROXIMITY_WINDOW_LINES:
            bullet_match = BULLET_MENTION_PATTERN.match(line)
            if bullet_match:
                names.add(bullet_match.group(1))

        if not line.strip():
            continue
        if FORWARD_DELEGATION_HEADER_PATTERN.search(line):
            lines_since_route_header = 0

    return names


def is_mentioned_as_delegate(agent_name: str, repo_root: Path) -> bool:
    """Whether any file forward-delegates to this agent via `@agent-name`.

    Scans agents/, commands/, and skills/ (recursively, any depth), since
    routing instructions for a subagent can live in a skill file the
    orchestrator loads rather than in orchestrator.md itself.
    """
    for dir_name in DELEGATION_SCAN_DIRS:
        scan_dir = repo_root / dir_name
        if not scan_dir.exists():
            continue
        for path in scan_dir.rglob("*.md"):
            if path.stem == agent_name:
                continue  # a file mentioning its own name isn't self-delegation
            text = path.read_text(encoding="utf-8-sig", errors="ignore")
            if agent_name in _forward_delegated_names_in_text(text):
                return True
    return False


def is_delegation_target(agent: Agent, all_agents: list[Agent], repo_root: Path) -> bool:
    """Whether this agent is set up to be delegated to, by any known signal.

    Neither signal proves a Task() call actually happens at runtime (see
    Gap 1 in the handoff — a granted permission, or even an instruction
    to route somewhere, is not proof the call occurs). This checks
    whether the file is *set up* to be delegated to, not whether
    delegation demonstrably occurs — that truth lives only in debug logs.
    """
    return is_named_via_permission(agent.name, all_agents) or is_mentioned_as_delegate(
        agent.name, repo_root
    )


def lint_mode_value(agent: Agent, all_agents: list[Agent], repo_root: Path) -> list[Issue]:
    if agent.mode not in VALID_MODES:
        return [Issue(agent.name, "mode-value", f"mode '{agent.mode}' is not one of {sorted(VALID_MODES)}")]

    is_delegated_to = is_delegation_target(agent, all_agents, repo_root)
    expected_mode = "subagent" if is_delegated_to else "primary"
    if agent.mode != expected_mode:
        return [
            Issue(
                agent.name,
                "mode-value",
                f"mode is '{agent.mode}' but usage suggests '{expected_mode}' "
                f"(delegation target found via permission.task or @mention: {is_delegated_to})",
            )
        ]
    return []


def find_cross_family_edges(agents: list[Agent], catalog: dict[str, str]) -> list[tuple[Agent, str, str, str]]:
    """Every delegation edge whose source and target use different families.

    Returns (delegator, target_name, source_family, target_family) tuples
    for reporting; this is informational, not a pass/fail check, since a
    cross-family edge is often intentional.
    """
    edges: list[tuple[Agent, str, str, str]] = []
    agents_by_name = {a.name: a for a in agents}

    for delegator in agents:
        source_family = catalog.get(delegator.model or "", "unknown")
        for target_name, decision in delegator.task_permissions.items():
            if decision != "allow" or target_name not in agents_by_name:
                continue
            target = agents_by_name[target_name]
            target_family = catalog.get(target.model or "", "unknown")
            if source_family != target_family:
                edges.append((delegator, target_name, source_family, target_family))
    return edges


def extract_required_denies(dec_dir: Path) -> dict[str, set[str]]:
    """Read every DEC file's `requires-deny` directives.

    Returns agent name -> set of permission paths (e.g. "task.general")
    that some DEC has declared must be denied.
    """
    required: dict[str, set[str]] = {}
    for path in dec_dir.glob("*.md"):
        text = path.read_text(encoding="utf-8-sig")
        for match in REQUIRES_DENY_PATTERN.finditer(text):
            required.setdefault(match["agent"], set()).add(match["permission"])
    return required


def validate_required_denies(agent: Agent, required: dict[str, set[str]]) -> list[Issue]:
    """Check every requires-deny directive that names this agent.

    Generalized over any permission category (task, bash, edit, write,
    external_directory, ...) via Agent.permission_value — not just
    `task.*`. This is what would have caught DEC-013's own documented
    silent reversion of `task: {"general": deny}` automatically, instead
    of it only surfacing later via a live headless-run hang.
    """
    permission_paths = required.get(agent.name)
    if not permission_paths:
        return []

    issues: list[Issue] = []
    for permission_path in permission_paths:
        actual = agent.permission_value(permission_path)
        if actual != "deny":
            issues.append(
                Issue(
                    agent.name,
                    "required-deny",
                    f"DEC requires {permission_path}=deny but found '{actual}' "
                    "(a prior fix may have been silently reverted)",
                )
            )
    return issues


def run_checks(repo_root: Path, agents_dir: Path, catalog_path: Path, dec_dir: Path) -> list[Issue]:
    agents = discover_agents(agents_dir)
    catalog = load_model_catalog(catalog_path)
    required_denies = extract_required_denies(dec_dir) if dec_dir.exists() else {}

    issues: list[Issue] = []
    for agent in agents:
        issues += validate_model_exists(agent, catalog)
        issues += lint_mode_value(agent, agents, repo_root)
        issues += validate_required_denies(agent, required_denies)

    cross_family_edges = find_cross_family_edges(agents, catalog)
    if cross_family_edges:
        print("Cross-family delegation edges (informational, not failures):")
        for delegator, target_name, source_family, target_family in cross_family_edges:
            print(f"  {delegator.name} ({source_family}) -> {target_name} ({target_family})")
        print()

    return issues


def main() -> int:
    repo_root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    agents_dir = repo_root / "agents"
    catalog_path = (
        Path(sys.argv[2])
        if len(sys.argv) > 2
        else repo_root / "docs" / "decisions" / "MODEL-ASSIGNMENT-MATRIX.md"
    )
    dec_dir = repo_root / "docs" / "decisions"

    issues = run_checks(repo_root, agents_dir, catalog_path, dec_dir)

    if not issues:
        print("All agent validation checks passed.")
        return 0

    print(f"{len(issues)} issue(s) found:\n")
    for issue in issues:
        print(f"  {issue}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())