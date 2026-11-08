"""File-tree snapshots for the runner (Phase 3B, plan step 3B.1).

snapshot maps every file under a folder to its content hash and ignores .git, so two
snapshots show what a run changed without trusting what the agent reports (plan section 5.6,
DEC-015 point 4). changed_files compares two snapshots and is pure. benchmark.py and the facts
stage share this module.
"""

import hashlib
from dataclasses import dataclass
from pathlib import Path


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
