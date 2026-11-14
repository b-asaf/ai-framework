"""File-tree snapshots for the runner (Phase 3B, plan step 3B.1).

snapshot maps every file under a folder to its content hash and ignores .git, so two
snapshots show what a run changed without trusting what the agent reports (plan section 5.6,
DEC-015 point 4). changed_files compares two snapshots and is pure. benchmark.py and the facts
stage share this module.
"""

import hashlib
from dataclasses import dataclass
from pathlib import Path

MAX_FILE_BYTES = 64 * 1024
MAX_TOTAL_BYTES = 256 * 1024


def snapshot(directory):
    """Map of relative path to content hash for every file under directory except .git."""
    root = Path(directory)
    result = {}
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        if path.is_file() and not relative.startswith(".git/"):
            result[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


@dataclass(frozen=True)
class Changes:
    added: tuple = ()
    modified: tuple = ()
    deleted: tuple = ()

    @property
    def everything(self):
        return tuple(sorted(self.added + self.modified + self.deleted))


def changed_files(before, after):
    """The files added, modified and deleted between two snapshots, each list sorted."""
    return Changes(
        added=tuple(sorted(set(after) - set(before))),
        modified=tuple(sorted(name for name in set(before) & set(after) if before[name] != after[name])),
        deleted=tuple(sorted(set(before) - set(after))),
    )


def _text(path, limit):
    """The UTF-8 text of a file, or None when it is missing, larger than limit bytes or not UTF-8."""
    try:
        if path.stat().st_size > limit:
            return None
        return path.read_bytes().decode("utf-8")
    except (OSError, ValueError):
        return None


def read_files(directory, names, max_file=MAX_FILE_BYTES, max_total=MAX_TOTAL_BYTES):
    """Name -> text of each named file under directory, so the content outlives the copy of the target.

    A file that is missing, larger than max_file bytes, not UTF-8 or past the max_total budget maps to None:
    None means not captured, never empty.
    """
    root = Path(directory)
    result, used = {}, 0
    for name in names:
        text = _text(root / name, min(max_file, max_total - used))
        result[name] = text
        used += len(text.encode("utf-8")) if text is not None else 0
    return result
