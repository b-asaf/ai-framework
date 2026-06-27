#!/usr/bin/env python3
"""
ai-framework setup script
=========================

TWO-STEP USAGE
--------------

Step 1 - Install once on this machine (run from the ai-framework folder):

    python setup.py --global

  Wires the framework globally for all AI tools detected on this machine.
  After this, opening ANY folder or workspace in OpenCode or VS Code
  automatically uses the framework - no per-project setup needed.

Step 2 - Add git hooks to a project (run from inside each git repo):

    python /path/to/ai-framework/setup.py --project

OTHER OPTIONS
-------------
  python setup.py --global --check     dry-run
  python setup.py --project --check    dry-run
  python setup.py --global --copy      copy instead of symlink (CI envs)
  python setup.py --help
"""

import argparse
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path

IS_WIN = platform.system() == "Windows"

def _c(code, text):
    return text if IS_WIN else f"\033[{code}m{text}\033[0m"

def ok(msg):   print(_c("0;32", f"  OK   {msg}"))
def warn(msg): print(_c("1;33", f"  WARN {msg}"))
def info(msg): print(_c("0;36", f"       {msg}"))
def bold(msg): print(_c("1",    msg))
def err(msg):  print(_c("0;31", f"  ERR  {msg}")); sys.exit(1)

# ── Paths ─────────────────────────────────────────────────────────────────────

REPO = Path(__file__).resolve().parent
HOME = Path.home()
CWD  = Path.cwd()

OPENCODE_GLOBAL  = HOME / ".config" / "opencode"
CLAUDE_DIR       = HOME / ".claude"
CODEX_DIR        = HOME / ".codex"
GEMINI_DIR       = HOME / ".gemini"
COPILOT_INTELLIJ = (
    Path(os.environ.get("LOCALAPPDATA", "")) / "github-copilot" / "intellij"
    if IS_WIN else None
)

if IS_WIN:
    VSCODE_SETTINGS = Path(os.environ.get("APPDATA", "")) / "Code" / "User" / "settings.json"
elif platform.system() == "Darwin":
    VSCODE_SETTINGS = HOME / "Library" / "Application Support" / "Code" / "User" / "settings.json"
else:
    VSCODE_SETTINGS = HOME / ".config" / "Code" / "User" / "settings.json"

INSTRUCTIONS = REPO / "instructions"
WRAPPERS     = INSTRUCTIONS / "wrappers"
SKILLS       = REPO / ".opencode" / "skills"
AGENTS       = REPO / ".opencode" / "agents"
COMMANDS     = REPO / ".opencode" / "commands"
HOOKS        = REPO / ".opencode" / "hooks"

RTK_BIN_DIR = HOME / ".ai-framework" / "bin"
RTK_EXE     = RTK_BIN_DIR / ("rtk.exe" if IS_WIN else "rtk")
RTK_RELEASE = "v0.42.4"
RTK_BASE_URL = f"https://github.com/rtk-ai/rtk/releases/download/{RTK_RELEASE}"
RTK_ARTIFACTS = {
    ("Windows", "x86_64"): "rtk-x86_64-pc-windows-msvc.zip",
    ("Darwin",  "x86_64"): "rtk-x86_64-apple-darwin.tar.gz",
    ("Darwin",  "aarch64"): "rtk-aarch64-apple-darwin.tar.gz",
    ("Linux",   "x86_64"): "rtk-x86_64-unknown-linux-musl.tar.gz",
    ("Linux",   "aarch64"): "rtk-aarch64-unknown-linux-gnu.tar.gz",
}

# ── Tool detection ────────────────────────────────────────────────────────────

def _detect():
    # RTK: check binary works (guards against the cargo name collision)
    rtk_candidate = shutil.which("rtk") or (str(RTK_EXE) if RTK_EXE.exists() else None)
    rtk_ok = False
    if rtk_candidate:
        try:
            r = subprocess.run([rtk_candidate, "--version"], capture_output=True, text=True)
            out = (r.stdout + r.stderr).lower()
            rtk_ok = r.returncode == 0 and "rtk" in out and "version" in out
        except Exception:
            pass

    return {
        "opencode":         bool(shutil.which("opencode") or OPENCODE_GLOBAL.exists()),
        "claude":           bool(shutil.which("claude")   or CLAUDE_DIR.exists()),
        "codex":            bool(shutil.which("codex")    or CODEX_DIR.exists()),
        "gemini":           bool(shutil.which("gemini")   or GEMINI_DIR.exists()),
        "copilot_intellij": IS_WIN and COPILOT_INTELLIJ is not None and COPILOT_INTELLIJ.exists(),
        "copilot_vscode":   bool(shutil.which("code") or VSCODE_SETTINGS.parent.exists() or VSCODE_SETTINGS.exists()),
        "rtk":              rtk_ok,
    }

# ── RTK auto-install ──────────────────────────────────────────────────────────

def install_rtk(dry):
    """Download and install RTK automatically. Returns rtk path or None."""

    # Already installed and working?
    existing = shutil.which("rtk") or (str(RTK_EXE) if RTK_EXE.exists() else None)
    if existing:
        try:
            r = subprocess.run([existing, "--version"], capture_output=True, text=True)
            if r.returncode == 0:
                ok(f"RTK already installed: {r.stdout.strip()}")
                return existing
            info("rtk binary exists but failed to run - reinstalling")
        except Exception:
            info("rtk binary exists but failed to run - reinstalling")

    if dry:
        info(f"would download RTK to {RTK_BIN_DIR}")
        return None

    arch = platform.machine().lower()
    if arch in ("amd64", "x86_64"):
        arch = "x86_64"
    elif arch in ("arm64", "aarch64"):
        arch = "aarch64"

    system = platform.system()
    artifact = RTK_ARTIFACTS.get((system, arch))
    if not artifact:
        warn(f"Unsupported platform/architecture for RTK auto-install: {system}/{arch}")
        info("Install manually: https://github.com/rtk-ai/rtk/releases")
        return None

    url = f"{RTK_BASE_URL}/{artifact}"
    checksum_url = f"{RTK_BASE_URL}/checksums.txt"
    is_zip = system == "Windows"

    RTK_BIN_DIR.mkdir(parents=True, exist_ok=True)
    tmp_archive = str(RTK_BIN_DIR / ("rtk-dl.zip" if is_zip else "rtk-dl.tar.gz"))

    def _sha256(path):
        import hashlib
        h = hashlib.sha256()
        with open(path, "rb") as fh:
            for chunk in iter(lambda: fh.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()

    try:
        info(f"Downloading RTK from GitHub releases...")
        urllib.request.urlretrieve(url, tmp_archive)

        info("Downloading RTK checksum manifest...")
        checksum_data = urllib.request.urlopen(checksum_url, timeout=30).read().decode("utf-8")

        expected = None
        for line in checksum_data.splitlines():
            line = line.strip()
            if not line or " " not in line:
                continue
            parts = line.split()
            if len(parts) >= 2 and parts[1].endswith(artifact):
                expected = parts[0]
                break

        if not expected:
            warn("Could not verify RTK checksum for downloaded artifact")
            return None

        actual = _sha256(tmp_archive)
        if actual != expected:
            warn("RTK checksum mismatch - aborting install")
            warn(f"expected {expected}")
            warn(f"actual   {actual}")
            return None

        if is_zip:
            with zipfile.ZipFile(tmp_archive, "r") as z:
                z.extractall(str(RTK_BIN_DIR))
        else:
            subprocess.run(["tar", "-xzf", tmp_archive, "-C", str(RTK_BIN_DIR)], check=True)

        Path(tmp_archive).unlink(missing_ok=True)

        if not IS_WIN:
            RTK_EXE.chmod(0o755)

        r = subprocess.run([str(RTK_EXE), "--version"], capture_output=True, text=True)
        if r.returncode == 0:
            ok(f"RTK installed: {r.stdout.strip()}")
            info(f"location: {RTK_EXE}")
            if not shutil.which("rtk"):
                warn(f"Add {RTK_BIN_DIR} to your PATH to use 'rtk' directly:")
                if IS_WIN:
                    info(f'  setx PATH "%PATH%;{RTK_BIN_DIR}"')
                else:
                    info(f'  echo \'export PATH="{RTK_BIN_DIR}:$PATH"\' >> ~/.bashrc')
            return str(RTK_EXE)
        else:
            warn(f"RTK installed but --version failed")
            return None

    except Exception as exc:
        warn(f"RTK download failed: {exc}")
        info("Install manually: https://github.com/rtk-ai/rtk/releases")
        return None


def wire_rtk(rtk_path, det, dry):
    """Run rtk init for each detected tool."""
    cmds = {
        "opencode": [rtk_path, "init", "--global", "--opencode"],
        "claude":   [rtk_path, "init", "--global"],
        "gemini":   [rtk_path, "init", "--global", "--gemini"],
        "codex":    None,
    }
    bold("Wiring RTK hooks...")
    for tool, cmd in cmds.items():
        if not det.get(tool):
            continue
        if cmd is None:
            info(f"rtk/{tool}: prompt-level - already in wrapper AGENTS.md")
            continue
        if dry:
            info(f"would run: {' '.join(cmd)}")
            continue
        try:
            subprocess.run(cmd, check=True)
            ok(f"rtk/{tool}")
        except (subprocess.CalledProcessError, FileNotFoundError) as exc:
            warn(f"rtk/{tool} failed: {exc}")

# ── VS Code global settings wiring ───────────────────────────────────────────

def wire_vscode_settings(dry):
    """Inject Copilot instruction paths into VS Code global settings.json.
    Wires VS Code Copilot globally - no per-project step needed.
    """
    code_instructions = [
        {"file": str(INSTRUCTIONS / "SHARED.md")},
        {"file": str(INSTRUCTIONS / "COPILOT.md")},
        {"file": str(INSTRUCTIONS / "VSCODE.md")},
    ]
    commit_instructions = [
        {"file": str(INSTRUCTIONS / "GIT_COMMIT.md")},
    ]

    if dry:
        info(f"would update {VSCODE_SETTINGS}")
        info("  github.copilot.chat.codeGeneration.instructions -> SHARED.md + COPILOT.md + VSCODE.md")
        info("  github.copilot.chat.commitMessageGeneration.instructions -> GIT_COMMIT.md")
        return

    settings = {}
    if VSCODE_SETTINGS.exists():
        try:
            content = VSCODE_SETTINGS.read_text(encoding="utf-8")
            if content.strip():
                # Strip JSON comments safely without removing quoted text
                clean = []
                in_string = False
                escape = False
                i = 0
                while i < len(content):
                    ch = content[i]
                    if ch == '\\' and not escape:
                        escape = True
                        clean.append(ch)
                        i += 1
                        continue
                    if ch == '"' and not escape:
                        in_string = not in_string
                        clean.append(ch)
                        i += 1
                        continue
                    escape = False
                    if not in_string and ch == '/' and i + 1 < len(content):
                        nxt = content[i + 1]
                        if nxt == '/':
                            i = content.find('\n', i + 2)
                            if i == -1:
                                break
                            clean.append('\n')
                            continue
                        if nxt == '*':
                            j = content.find('*/', i + 2)
                            i = j + 2 if j != -1 else len(content)
                            continue
                    clean.append(ch)
                    i += 1
                settings = json.loads(''.join(clean))
        except Exception as exc:
            warn(f"Could not parse {VSCODE_SETTINGS}: {exc}")
            warn("Skipping VS Code settings wiring - fix manually if needed")
            return
    else:
        VSCODE_SETTINGS.parent.mkdir(parents=True, exist_ok=True)

    def _merge_instruction_list(key, desired):
        existing = settings.get(key)
        if not isinstance(existing, list):
            existing = []
        merged = []
        for item in existing + desired:
            if item not in merged:
                merged.append(item)
        settings[key] = merged

    _merge_instruction_list("github.copilot.chat.codeGeneration.instructions", code_instructions)
    _merge_instruction_list("github.copilot.chat.commitMessageGeneration.instructions", commit_instructions)

    VSCODE_SETTINGS.write_text(json.dumps(settings, indent=2, ensure_ascii=False), encoding="utf-8")
    ok(str(VSCODE_SETTINGS))
    info("  codeGeneration.instructions:       SHARED.md + COPILOT.md + VSCODE.md")
    info("  commitMessageGeneration.instructions: GIT_COMMIT.md")

# ── Link maps ─────────────────────────────────────────────────────────────────

def global_links(det):
    """All links wired globally - works for every folder/workspace automatically."""
    links = []

    if det["opencode"]:
        links += [
            (OPENCODE_GLOBAL / "opencode.json", REPO / "opencode.json",          "file"),
            (OPENCODE_GLOBAL / "AGENTS.md",     WRAPPERS / "opencode-AGENTS.md", "file"),
            (OPENCODE_GLOBAL / "agents",         AGENTS,                           "dir"),
            (OPENCODE_GLOBAL / "skills",         SKILLS,                           "dir"),
            (OPENCODE_GLOBAL / "commands",       COMMANDS,                         "dir"),
            (OPENCODE_GLOBAL / "hooks",          HOOKS,                            "dir"),
        ]

    if det["claude"]:
        links += [
            (CLAUDE_DIR / "CLAUDE.md",  INSTRUCTIONS / "CLAUDE.md", "file"),
            (CLAUDE_DIR / "skills",     SKILLS,                      "dir"),
            (CLAUDE_DIR / "agents",     AGENTS,                      "dir"),
            (CLAUDE_DIR / "commands",   COMMANDS,                    "dir"),
            (CLAUDE_DIR / "hooks",      HOOKS,                       "dir"),
        ]

    if det["codex"]:
        links += [
            (CODEX_DIR / "AGENTS.md", WRAPPERS / "codex-AGENTS.md", "file"),
        ]

    if det["gemini"]:
        links += [
            (GEMINI_DIR / "GEMINI.md", INSTRUCTIONS / "GEMINI.md", "file"),
            (GEMINI_DIR / "skills",    SKILLS,                      "dir"),
        ]

    if det["copilot_intellij"] and IS_WIN and COPILOT_INTELLIJ:
        links += [
            (COPILOT_INTELLIJ / "global-copilot-instructions.md",
             INSTRUCTIONS / "COPILOT.md",         "file"),
            (COPILOT_INTELLIJ / "global-agents-instructions.md",
             WRAPPERS / "opencode-AGENTS.md",      "file"),
            (COPILOT_INTELLIJ / "global-git-commit-instructions.md",
             INSTRUCTIONS / "GIT_COMMIT.md",       "file"),
        ]

    return links

# ── Git hooks ─────────────────────────────────────────────────────────────────

def install_hooks(dry):
    script  = REPO / ".opencode" / "verification" / "scripts" / "install-hooks.sh"
    git_dir = CWD / ".git"
    if not script.exists():
        warn("Git hooks script not found: .opencode/verification/scripts/install-hooks.sh")
        return
    if not git_dir.exists():
        warn(f"No .git directory in {CWD} - run --project from inside a git repo root")
        return
    if dry:
        info(f"would run: bash {script.relative_to(REPO)}")
        return
    try:
        subprocess.run(["bash", str(script)], check=True, cwd=CWD)
        ok("Git hooks installed")
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        warn(f"Git hooks install failed: {exc}")

# ── Symlink / copy helpers ────────────────────────────────────────────────────

def _remove(path):
    if not path.exists() and not path.is_symlink():
        return
    if path.is_symlink() or (IS_WIN and _is_junction(path)):
        if path.is_symlink():
            path.unlink(missing_ok=True)
        else:
            path.rmdir()
        return
    base = path.with_suffix(path.suffix + ".bak")
    bak = base
    counter = 1
    while bak.exists():
        bak = base.with_name(f"{base.name}.{counter}")
        counter += 1
    info(f"backing up {path.name} -> {bak.name}")
    path.rename(bak)

def _is_junction(path):
    try:
        import ctypes
        return bool(ctypes.windll.kernel32.GetFileAttributesW(str(path)) & 0x400)
    except Exception:
        return False

def _symlink(link, target, kind):
    link.parent.mkdir(parents=True, exist_ok=True)
    _remove(link)
    if IS_WIN and kind == "dir":
        subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(target)],
                       check=True, capture_output=True)
    else:
        link.symlink_to(target, target_is_directory=(kind == "dir"))

def _copy(link, target, kind):
    link.parent.mkdir(parents=True, exist_ok=True)
    _remove(link)
    shutil.copytree(target, link) if kind == "dir" else shutil.copy2(target, link)

def _apply(links, mode, dry):
    done, skipped = [], []
    for link, target, kind in links:
        if not target.exists():
            skipped.append((link, target))
            try:
                rel = target.relative_to(REPO)
            except ValueError:
                rel = target
            warn(f"SKIP {link.name}  (source not found: {rel})")
            continue
        try:
            label = Path("~") / link.relative_to(HOME)
        except ValueError:
            label = link
        if dry:
            try:
                rel_t = target.relative_to(REPO)
            except ValueError:
                rel_t = target
            info(f"would {'link' if mode == 'symlink' else 'copy'}  {label}  ->  {rel_t}")
            done.append(link)
            continue
        try:
            (_symlink if mode == "symlink" else _copy)(link, target, kind)
            ok(str(label))
            done.append(link)
        except Exception as exc:
            warn(f"FAIL {label}  ({exc})")
            skipped.append((link, target))
    return done, skipped

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Wire ai-framework into AI tools on this machine.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--global",  dest="do_global",  action="store_true",
                       help="Wire globally - run once per machine from the framework folder")
    group.add_argument("--project", dest="do_project", action="store_true",
                       help="Install git hooks into current repo - run once per repo")
    parser.add_argument("--copy",  action="store_true", help="Copy instead of symlink")
    parser.add_argument("--check", action="store_true", help="Dry-run: show what would happen")
    args = parser.parse_args()

    mode = "copy" if args.copy else "symlink"
    dry  = args.check
    det  = _detect()

    print()
    bold("ai-framework setup")
    bold("=" * 44)
    info(f"repo:  {REPO}")
    info(f"mode:  {'dry-run (--check)' if dry else mode}")
    info(f"step:  {'--global (once per machine)' if args.do_global else '--project (once per repo)'}")
    print()

    labels = {
        "opencode":         "OpenCode          [PRIMARY]",
        "claude":           "Claude Code",
        "codex":            "Codex CLI",
        "gemini":           "Gemini CLI",
        "copilot_intellij": "Copilot IntelliJ  (Windows)",
        "copilot_vscode":   "Copilot VS Code",
        "rtk":              "RTK",
    }
    bold("Detected tools:")
    for key, label in labels.items():
        found  = det.get(key, False)
        status = _c("0;32", "found") if found else _c("0;90", "not found")
        print(f"     {label:<34} {status}")
    print()

    if args.do_global:
        # 1. Symlinks / dir junctions
        bold("Wiring symlinks...")
        links = global_links(det)
        done, skipped = _apply(links, mode, dry)

        # 2. VS Code global settings.json
        if det["copilot_vscode"]:
            print()
            bold("Wiring VS Code Copilot (global settings.json)...")
            wire_vscode_settings(dry)

        # 3. RTK - auto-install if missing, then wire
        print()
        bold("Setting up RTK token reduction...")
        if not det["rtk"]:
            rtk_path = install_rtk(dry)
        else:
            ok("RTK already installed")
            rtk_path = shutil.which("rtk") or str(RTK_EXE)

        if rtk_path and not dry:
            wire_rtk(rtk_path, det, dry)
        elif dry:
            wire_rtk("rtk", det, dry)

        print()
        bold("=" * 44)
        if dry:
            bold(f"Dry run complete - {len(done)} entries would be wired.")
        else:
            bold(f"Global setup done - {len(done)} wired, {len(skipped)} skipped.")
            print()
            bold("What works now (every folder and workspace):")
            info("  OpenCode:        open any folder - framework is active")
            info("  VS Code Copilot: open any folder - framework is active")
            info("  Claude Code:     open any folder - framework is active")
            info("")
            info("Next step (optional, per repo):")
            info("  cd your-project && python setup.py --project")
            info("  (installs git hooks: pre-commit, pre-push, commit-msg)")

        if skipped:
            print()
            warn("Skipped (source missing in repo):")
            for link, target in skipped:
                try:
                    rel = target.relative_to(REPO)
                except ValueError:
                    rel = target
                info(f"  {link.name}  <-  {rel}")

    elif args.do_project:
        if not (CWD / ".git").exists():
            err(f"{CWD} is not a git repo root. cd into your project repo first.")

        bold(f"Installing git hooks into: {CWD.name}")
        print()
        install_hooks(dry)

        print()
        bold("=" * 44)
        if not dry:
            bold("Project setup done.")
            info("  pre-commit, pre-push, commit-msg hooks are now active")
            info("  Everything else already works from --global setup")

    print()


if __name__ == "__main__":
    main()
