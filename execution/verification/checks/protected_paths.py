"""Protected-paths check (Phase 3A, plan step 3A.2, DEC-015).

Protected paths are versioned data (`constraints.protected_paths`), enforced
by comparing the working tree before and after a run (plan section 5.6). The
check does not rely on what the agent reports; it hashes the files under
each protected path and compares two snapshots.

`snapshot` is the only function that touches the filesystem. `find_violations`
is a pure function: given two snapshots, it reports every file that was
added, removed, or changed. An unreadable protected file raises instead of
being silently skipped (fail closed, DEC-015).
"""

import hashlib
import posixpath
from pathlib import Path


class ProtectedPathError(Exception):
    """A protected path exists but could not be read, or is unsafe."""


def _normalize_protected_path(protected_path):
    """Normalize protected_path and reject empty/root/escaping values (fail closed).

    Rejects absolute protected_path values, anything that normalizes to "."
    or "" (which would silently protect nothing while matching everything),
    and anything that escapes root via `..` components.
    """
    if Path(protected_path).is_absolute():
        raise ProtectedPathError(f"protected_path must be relative: {protected_path}")
    slashed = str(protected_path).replace("\\", "/")
    if slashed.startswith("/"):
        raise ProtectedPathError(f"protected_path must be relative: {protected_path}")
    normalized = posixpath.normpath(slashed)
    if normalized in (".", ""):
        raise ProtectedPathError(f"protected_path must not be empty or '.': {protected_path!r}")
    if normalized == ".." or normalized.startswith("../"):
        raise ProtectedPathError(f"protected_path escapes root: {protected_path}")
    return normalized


def _resolve_within_root(root, protected_path):
    """Resolve protected_path under root, rejecting escapes (fail closed).

    Rejects absolute protected_path values and any resolved location that
    falls outside root (e.g. via `..` components).
    """
    normalized = _normalize_protected_path(protected_path)
    resolved_root = root.resolve()
    candidate = root / normalized
    # Resolve the parent directory (not the final component) so a protected
    # path that is itself a symlink isn't dereferenced during containment
    # checking; only `..`/junction-style escapes in the path itself matter.
    resolved_parent = candidate.parent.resolve()
    if resolved_root != resolved_parent and resolved_root not in resolved_parent.parents:
        raise ProtectedPathError(f"protected_path escapes root: {protected_path}")
    return candidate


def _iter_files(root, protected_path):
    """Yield every file under root/protected_path that currently exists."""
    target = _resolve_within_root(root, protected_path)
    if target.is_symlink() or target.is_file():
        yield target
    elif target.is_dir():
        yield from (
            path for path in target.rglob("*") if path.is_symlink() or path.is_file()
        )


def _hash_file(path):
    if path.is_symlink():
        try:
            target = path.readlink().as_posix()
        except OSError as error:
            raise ProtectedPathError(f"cannot read protected symlink {path}: {error}") from error
        return "symlink:" + hashlib.sha256(target.encode("utf-8")).hexdigest()
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as error:
        raise ProtectedPathError(f"cannot read protected file {path}: {error}") from error


def snapshot(root, protected_paths):
    """Hash every file currently under each of protected_paths, relative to root.

    Returns a dict mapping posix-relative-path -> sha256 hex digest. A
    protected path that does not exist yet is simply absent from the result.
    A protected path that exists but cannot be read raises ProtectedPathError.
    """
    root = Path(root)
    hashes = {}
    for protected_path in protected_paths:
        for file_path in _iter_files(root, protected_path):
            relative = file_path.relative_to(root).as_posix()
            hashes[relative] = _hash_file(file_path)
    return hashes


def _owning_protected_path(path, protected_paths):
    for protected_path in protected_paths:
        normalized = _normalize_protected_path(protected_path)
        if path == normalized or path.startswith(normalized + "/"):
            return protected_path
    return None


def find_violations(before, after, protected_paths):
    """Return one violation per protected file that changed between two snapshots.

    Pure function: no filesystem access. before/after are dicts from
    snapshot(); only entries that fall under one of protected_paths are
    considered, so passing broader snapshots is safe.
    """
    violations = []
    for protected_path in protected_paths:
        _normalize_protected_path(protected_path)
    for path in sorted(set(before) | set(after)):
        owner = _owning_protected_path(path, protected_paths)
        if owner is None:
            continue
        if path not in before:
            violations.append({"path": path, "protected_path": owner, "reason": "added"})
        elif path not in after:
            violations.append({"path": path, "protected_path": owner, "reason": "removed"})
        elif before[path] != after[path]:
            violations.append({"path": path, "protected_path": owner, "reason": "modified"})
    return violations
