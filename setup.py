#!/usr/bin/env python3
"""
ai-framework setup script
=========================
Wires the framework into every AI tool on this machine via symlinks (Mac/Linux)
or directory junctions / file copies (Windows).

Supported tools
---------------
  Claude Code   ~/.claude/
  OpenCode      ~/.config/opencode/   (also reads ~/.claude/ as fallback)
  Codex CLI     ~/.codex/
  Copilot       %LOCALAPPDATA%/github-copilot/intellij/   (Windows only)

Usage
-----
  python setup.py              # link into all detected tools
  python setup.py --copy       # copy instead of symlink (CI / no-symlink envs)
  python setup.py --check      # dry-run: show what would be linked / copied
  python setup.py --help
"""

import argparse
import os
import platform
import shutil
import sys
from pathlib import Path

# ── Colour helpers (no deps) ─────────────────────────────────────────────────

IS_WIN = platform.system() == "Windows"

def _c(code: str, text: str) -> str:
    if IS_WIN:
        return text
    return f"\033[{code}m{text}\033[0m"

def ok(msg: str)   -> None: print(_c("0;32", f"  ✔  {msg}"))
def warn(msg: str) -> None: print(_c("1;33", f"  ⚠  {msg}"))
def err(msg: str)  -> None: print(_c("0;31", f"  ✘  {msg}")); sys.exit(1)
def info(msg: str) -> None: print(_c("0;36", f"     {msg}"))
def bold(msg: str) -> None: print(_c("1",    msg))

# ── Resolve paths ────────────────────────────────────────────────────────────

REPO = Path(__file__).resolve().parent
HOME = Path.home()

CLAUDE_DIR  = HOME / ".claude"
OPENCODE_DIR = HOME / ".config" / "opencode"
CODEX_DIR   = HOME / ".codex"
COPILOT_DIR = (
    Path(os.environ.get("LOCALAPPDATA", "")) / "github-copilot" / "intellij"
    if IS_WIN else None
)

# ── Link map: (link_path, target_relative_to_repo, kind) ────────────────────
#   kind = "file" | "dir"

def build_link_map() -> list[tuple[Path, Path, str]]:
    i = REPO / "instructions"
    links = [
        # Claude Code
        (CLAUDE_DIR / "CLAUDE.md",       i / "CLAUDE.md",  "file"),
        (CLAUDE_DIR / "skills",          REPO / "skills",   "dir"),
        (CLAUDE_DIR / "agents",          REPO / "agents",   "dir"),

        # OpenCode  (reads instructions/SHARED.md directly; also inherits ~/.claude)
        (OPENCODE_DIR / "AGENTS.md",     i / "SHARED.md",  "file"),

        # Codex CLI
        (CODEX_DIR / "AGENTS.md",        i / "SHARED.md",  "file"),
    ]

    # Copilot IntelliJ — Windows only, skip silently on other OS
    if COPILOT_DIR is not None:
        links += [
            (COPILOT_DIR / "global-copilot-instructions.md",   i / "COPILOT.md",    "file"),
            (COPILOT_DIR / "global-agents-instructions.md",    i / "SHARED.md",     "file"),
            (COPILOT_DIR / "global-git-commit-instructions.md", i / "GIT_COMMIT.md", "file"),
        ]

    return links

# ── Core helpers ─────────────────────────────────────────────────────────────

def _remove_existing(path: Path) -> None:
    """Remove a symlink/junction. Back up real files/dirs."""
    if not path.exists() and not path.is_symlink():
        return
    if path.is_symlink() or (IS_WIN and _is_junction(path)):
        path.unlink(missing_ok=True)
        return
    # Real content — back up
    backup = path.with_suffix(path.suffix + ".bak")
    info(f"backing up {path.name} → {backup.name}")
    if backup.exists():
        shutil.rmtree(backup) if backup.is_dir() else backup.unlink()
    path.rename(backup)


def _is_junction(path: Path) -> bool:
    """Windows junction detection (os.path.islink doesn't catch junctions)."""
    try:
        import ctypes
        FILE_ATTRIBUTE_REPARSE_POINT = 0x400
        attrs = ctypes.windll.kernel32.GetFileAttributesW(str(path))
        return bool(attrs & FILE_ATTRIBUTE_REPARSE_POINT)
    except Exception:
        return False


def _make_symlink(link: Path, target: Path, kind: str) -> None:
    link.parent.mkdir(parents=True, exist_ok=True)
    _remove_existing(link)
    if IS_WIN and kind == "dir":
        # Use junction for dirs on Windows (no admin required)
        import subprocess
        subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(target)],
                       check=True, capture_output=True)
    else:
        link.symlink_to(target, target_is_directory=(kind == "dir"))


def _make_copy(link: Path, target: Path, kind: str) -> None:
    link.parent.mkdir(parents=True, exist_ok=True)
    _remove_existing(link)
    if kind == "dir":
        shutil.copytree(target, link)
    else:
        shutil.copy2(target, link)

# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Wire ai-framework into all AI tools on this machine.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--copy", action="store_true",
        help="Copy files instead of symlinking (useful in CI or restricted envs)"
    )
    parser.add_argument(
        "--check", action="store_true",
        help="Dry-run: show what would be done without making any changes"
    )
    args = parser.parse_args()

    mode = "copy" if args.copy else "symlink"
    dry  = args.check

    print()
    bold("ai-framework setup")
    bold("=" * 40)
    info(f"repo:   {REPO}")
    info(f"mode:   {'dry-run (--check)' if dry else mode}")
    print()

    links = build_link_map()
    skipped = []
    done    = []

    for link, target, kind in links:
        if not target.exists():
            skipped.append((link, target))
            warn(f"SKIP  {link.name}  (source not found: {target.relative_to(REPO)})")
            continue

        rel_link = link
        try:
            rel_link = link.relative_to(HOME)
            rel_link = Path("~") / rel_link
        except ValueError:
            pass

        if dry:
            info(f"would {'link' if mode == 'symlink' else 'copy'}  {rel_link}  →  {target.relative_to(REPO)}")
            done.append(link)
            continue

        try:
            if mode == "symlink":
                _make_symlink(link, target, kind)
            else:
                _make_copy(link, target, kind)
            ok(f"{rel_link}")
            done.append(link)
        except Exception as exc:  # noqa: BLE001
            warn(f"FAIL  {rel_link}  ({exc})")
            skipped.append((link, target))

    # ── Summary ───────────────────────────────────────────────────────────────
    print()
    bold("─" * 40)
    if dry:
        bold(f"Dry run complete — {len(done)} entries would be processed.")
    else:
        bold(f"Done — {len(done)} entries {'linked' if mode == 'symlink' else 'copied'}, "
             f"{len(skipped)} skipped.")

    if skipped:
        print()
        warn("Skipped entries (source files not found in repo):")
        for link, target in skipped:
            info(f"  {link.name}  ←  {target.relative_to(REPO)}")
        info("Run again after adding the missing files.")

    if not dry:
        print()
        bold("Next steps:")
        info("  1. Open your workspace root in the AI tool of your choice")
        info("  2. First-run analysis will execute automatically")
        info("  3. Confirm the detected stack and conventions")
        info("  4. Review docs/refactoring-plan.md if generated")
        info("  5. To update later: git pull  (symlinks update instantly)")
        print()
        info("Read workflow-guide.md for day-to-day usage.")
    print()


if __name__ == "__main__":
    main()
