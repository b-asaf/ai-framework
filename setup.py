#!/usr/bin/env python3
"""
ai-framework setup script
=========================
Wires the framework into every AI tool on this machine via symlinks (Mac/Linux)
or directory junctions / file copies (Windows).

Supported tools
---------------
  Claude Code   ~/.claude/
  OpenCode      ~/.config/opencode/
  Codex CLI     ~/.codex/
  Gemini CLI    ~/.gemini/
  Cursor        ~/.cursor/rules/
  Windsurf      ~/.codeium/windsurf/memories/   (global rules)
  VS Code       .github/copilot-instructions.md (project-level only — run from repo root)
  Copilot       %LOCALAPPDATA%/github-copilot/intellij/  (Windows only)

Usage
-----
  python setup.py                  # link into all detected tools
  python setup.py --copy           # copy instead of symlink (CI / no-symlink envs)
  python setup.py --check          # dry-run: show what would be linked / copied
  python setup.py --install-hooks  # also install git hooks into .git/hooks/
  python setup.py --help
"""

import argparse
import os
import platform
import shutil
import subprocess
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
def info(msg: str) -> None: print(_c("0;36", f"     {msg}"))
def bold(msg: str) -> None: print(_c("1",    msg))
def err(msg: str)  -> None: print(_c("0;31", f"  ✘  {msg}")); sys.exit(1)

# ── Resolve paths ────────────────────────────────────────────────────────────

REPO = Path(__file__).resolve().parent
HOME = Path.home()

CLAUDE_DIR   = HOME / ".claude"
OPENCODE_DIR = HOME / ".config" / "opencode"
CODEX_DIR    = HOME / ".codex"
GEMINI_DIR   = HOME / ".gemini"
CURSOR_DIR   = HOME / ".cursor" / "rules"
WINDSURF_DIR = HOME / ".codeium" / "windsurf" / "memories"
COPILOT_DIR  = (
    Path(os.environ.get("LOCALAPPDATA", "")) / "github-copilot" / "intellij"
    if IS_WIN else None
)

# ── Tool detection ────────────────────────────────────────────────────────────

def _detect_installed_tools() -> dict:
    """Detect which AI tools are actually installed on this machine."""
    return {
        "claude":   bool(shutil.which("claude")   or CLAUDE_DIR.exists()),
        "opencode": bool(shutil.which("opencode") or OPENCODE_DIR.exists()),
        "codex":    bool(shutil.which("codex")    or CODEX_DIR.exists()),
        "gemini":   bool(shutil.which("gemini")   or GEMINI_DIR.exists()),
        "cursor":   bool(shutil.which("cursor")   or (HOME / ".cursor").exists()),
        "windsurf": bool(shutil.which("windsurf") or (HOME / ".codeium").exists()),
        "vscode":   bool(shutil.which("code")),
        "copilot":  IS_WIN and COPILOT_DIR is not None and COPILOT_DIR.exists(),
    }

# ── Link map ─────────────────────────────────────────────────────────────────
# Each entry: (link_path, target_path, kind, tool_key)
# kind     = "file" | "dir"
# tool_key = key from _detect_installed_tools(); None = always wire

def build_link_map(detected: dict) -> list:
    i   = REPO / "instructions"
    # Skills and agents live in .opencode/ — correct path
    skl = REPO / ".opencode" / "skills"
    agt = REPO / ".opencode" / "agents"

    links = [
        # Claude Code
        (CLAUDE_DIR / "CLAUDE.md",           i / "CLAUDE.md",   "file", "claude"),
        (CLAUDE_DIR / "skills",              skl,                "dir",  "claude"),
        (CLAUDE_DIR / "agents",              agt,                "dir",  "claude"),

        # OpenCode
        (OPENCODE_DIR / "AGENTS.md",         i / "SHARED.md",   "file", "opencode"),

        # Codex CLI
        (CODEX_DIR / "AGENTS.md",            i / "SHARED.md",   "file", "codex"),

        # Gemini CLI
        (GEMINI_DIR / "GEMINI.md",           i / "GEMINI.md",   "file", "gemini"),

        # Cursor
        (CURSOR_DIR / "shared.mdc",          i / "CURSOR.md",   "file", "cursor"),

        # Windsurf
        (WINDSURF_DIR / "global-rules.md",   i / "WINDSURF.md", "file", "windsurf"),
    ]

    # VS Code Copilot — project-level only; wire into CWD/.github/
    if detected.get("vscode"):
        vscode_target = Path.cwd() / ".github" / "copilot-instructions.md"
        links.append((vscode_target, i / "VSCODE.md", "file", "vscode"))

    # Copilot IntelliJ — Windows only
    if IS_WIN and COPILOT_DIR is not None and detected.get("copilot"):
        links += [
            (COPILOT_DIR / "global-copilot-instructions.md",    i / "COPILOT.md",    "file", "copilot"),
            (COPILOT_DIR / "global-agents-instructions.md",     i / "SHARED.md",     "file", "copilot"),
            (COPILOT_DIR / "global-git-commit-instructions.md", i / "GIT_COMMIT.md", "file", "copilot"),
        ]

    return links

# ── Git hooks installer ───────────────────────────────────────────────────────

def install_git_hooks(dry: bool) -> None:
    hook_script = REPO / ".opencode" / "verification" / "scripts" / "install-hooks.sh"
    git_dir     = Path.cwd() / ".git"

    if not hook_script.exists():
        warn("Git hooks script not found: .opencode/verification/scripts/install-hooks.sh")
        return
    if not git_dir.exists():
        warn(f"No .git directory in {Path.cwd()} — run setup.py from inside a git repo")
        return
    if dry:
        info(f"would run: bash {hook_script.relative_to(REPO)}")
        return
    try:
        subprocess.run(["bash", str(hook_script)], check=True, cwd=Path.cwd())
        ok("Git hooks installed")
    except subprocess.CalledProcessError as exc:
        warn(f"Git hooks install failed: {exc}")
    except FileNotFoundError:
        warn("bash not found — cannot install git hooks on this platform")

# ── Core symlink / copy helpers ───────────────────────────────────────────────

def _remove_existing(path: Path) -> None:
    if not path.exists() and not path.is_symlink():
        return
    if path.is_symlink() or (IS_WIN and _is_junction(path)):
        path.unlink(missing_ok=True)
        return
    backup = path.with_suffix(path.suffix + ".bak")
    info(f"backing up {path.name} → {backup.name}")
    if backup.exists():
        shutil.rmtree(backup) if backup.is_dir() else backup.unlink()
    path.rename(backup)

def _is_junction(path: Path) -> bool:
    try:
        import ctypes
        return bool(ctypes.windll.kernel32.GetFileAttributesW(str(path)) & 0x400)
    except Exception:
        return False

def _make_symlink(link: Path, target: Path, kind: str) -> None:
    link.parent.mkdir(parents=True, exist_ok=True)
    _remove_existing(link)
    if IS_WIN and kind == "dir":
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
    parser.add_argument("--copy",          action="store_true",
                        help="Copy files instead of symlinking")
    parser.add_argument("--check",         action="store_true",
                        help="Dry-run: show what would happen without changes")
    parser.add_argument("--install-hooks", action="store_true",
                        help="Also install git hooks into .git/hooks/")
    args = parser.parse_args()

    mode = "copy" if args.copy else "symlink"
    dry  = args.check

    print()
    bold("ai-framework setup")
    bold("=" * 40)
    info(f"repo:   {REPO}")
    info(f"mode:   {'dry-run (--check)' if dry else mode}")
    print()

    detected = _detect_installed_tools()
    bold("Detected tools:")
    for tool, found in detected.items():
        status = _c("0;32", "✔ found") if found else _c("0;90", "– not found (will skip)")
        print(f"     {tool:<12} {status}")
    print()

    links   = build_link_map(detected)
    skipped = []
    done    = []

    for link, target, kind, tool_key in links:
        if tool_key and not detected.get(tool_key, False):
            continue
        if not target.exists():
            skipped.append((link, target))
            try:
                rel = target.relative_to(REPO)
            except ValueError:
                rel = target
            warn(f"SKIP  {link.name}  (source not found: {rel})")
            continue

        try:
            rel_link = Path("~") / link.relative_to(HOME)
        except ValueError:
            rel_link = link

        if dry:
            try:
                rel_tgt = target.relative_to(REPO)
            except ValueError:
                rel_tgt = target
            info(f"would {'link' if mode == 'symlink' else 'copy'}  {rel_link}  →  {rel_tgt}")
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

    if args.install_hooks:
        print()
        bold("Installing git hooks...")
        install_git_hooks(dry)

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
            try:
                rel = target.relative_to(REPO)
            except ValueError:
                rel = target
            info(f"  {link.name}  ←  {rel}")
        info("Run again after adding the missing files.")

    if not dry:
        print()
        bold("Next steps:")
        info("  1. Open your workspace root in the AI tool of your choice")
        info("  2. First-run analysis will execute automatically")
        info("  3. Confirm the detected stack and conventions")
        info("  4. Review docs/refactoring-plan.md if generated")
        info("  5. To update later: git pull  (symlinks update instantly)")
        if not args.install_hooks:
            info("  6. To install git hooks: python setup.py --install-hooks")
        print()
        info("Read workflow-guide.md for day-to-day usage.")
    print()


if __name__ == "__main__":
    main()
