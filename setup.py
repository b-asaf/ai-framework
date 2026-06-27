#!/usr/bin/env python3
"""
ai-framework setup
==================
Run once per machine from the ai-framework folder.
Re-run to repair broken links or wire newly installed tools.

    python setup.py

No flags needed. The script detects installed tools automatically.
"""

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

REPO = Path(__file__).resolve().parent
HOME = Path.home()

# ── Target locations ──────────────────────────────────────────────────────────

OPENCODE_DIR     = HOME / ".config" / "opencode"
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

# ── Repo source paths ─────────────────────────────────────────────────────────

AGENTS_MD    = REPO / "AGENTS.md"
OPENCODE_CFG = REPO / "opencode.json"
INSTRUCTIONS = REPO / "instructions"
SKILLS       = REPO / "skills"
AGENTS       = REPO / "agents"
COMMANDS     = REPO / "commands"
HOOKS        = REPO / "hooks"

RTK_BIN_DIR = REPO / "bin"
RTK_EXE     = RTK_BIN_DIR / ("rtk.exe" if IS_WIN else "rtk")
RTK_URLS    = {
    "Windows": "https://github.com/rtk-ai/rtk/releases/latest/download/rtk-x86_64-pc-windows-msvc.zip",
    "Darwin":  "https://github.com/rtk-ai/rtk/releases/latest/download/rtk-x86_64-apple-darwin.tar.gz",
    "Linux":   "https://github.com/rtk-ai/rtk/releases/latest/download/rtk-x86_64-unknown-linux-musl.tar.gz",
}

# ── Tool detection ────────────────────────────────────────────────────────────

def detect():
    rtk_candidate = shutil.which("rtk") or (str(RTK_EXE) if RTK_EXE.exists() else None)
    rtk_ok = False
    if rtk_candidate:
        try:
            r = subprocess.run([rtk_candidate, "--version"], capture_output=True, text=True)
            rtk_ok = r.returncode == 0
        except Exception:
            pass
    return {
        "opencode": bool(shutil.which("opencode") or OPENCODE_DIR.exists()),
        "claude":   bool(shutil.which("claude")   or CLAUDE_DIR.exists()),
        "codex":    bool(shutil.which("codex")    or CODEX_DIR.exists()),
        "gemini":   bool(shutil.which("gemini")   or GEMINI_DIR.exists()),
        "copilot_intellij": IS_WIN and COPILOT_INTELLIJ is not None and COPILOT_INTELLIJ.exists(),
        "copilot_vscode":   bool(shutil.which("code") or VSCODE_SETTINGS.exists()),
        "rtk":      rtk_ok,
    }

# ── Link table ────────────────────────────────────────────────────────────────

def build_links(det):
    links = []

    if det["opencode"]:
        links += [
            (OPENCODE_DIR / "opencode.json", OPENCODE_CFG,                      "file"),
            (OPENCODE_DIR / "AGENTS.md",     AGENTS_MD,                          "file"),
            (OPENCODE_DIR / "agents",        AGENTS,                             "dir"),
            (OPENCODE_DIR / "skills",        SKILLS,                             "dir"),
            (OPENCODE_DIR / "commands",      COMMANDS,                           "dir"),
            (OPENCODE_DIR / "hooks",         HOOKS,                              "dir"),
        ]

    if det["claude"]:
        links += [
            (CLAUDE_DIR / "CLAUDE.md",  INSTRUCTIONS / "CLAUDE.md", "file"),
            (CLAUDE_DIR / "AGENTS.md",  AGENTS_MD,                  "file"),
            (CLAUDE_DIR / "agents",     AGENTS,                     "dir"),
            (CLAUDE_DIR / "skills",     SKILLS,                     "dir"),
            (CLAUDE_DIR / "commands",   COMMANDS,                   "dir"),
            (CLAUDE_DIR / "hooks",      HOOKS,                      "dir"),
        ]

    if det["codex"]:
        links += [
            (CODEX_DIR / "AGENTS.md", INSTRUCTIONS / "codex-AGENTS.md", "file"),
        ]

    if det["gemini"]:
        links += [
            (GEMINI_DIR / "GEMINI.md", INSTRUCTIONS / "GEMINI.md", "file"),
            (GEMINI_DIR / "skills",    SKILLS,                     "dir"),
        ]

    if det["copilot_intellij"] and IS_WIN and COPILOT_INTELLIJ:
        links += [
            (COPILOT_INTELLIJ / "global-copilot-instructions.md",
             INSTRUCTIONS / "COPILOT.md",   "file"),
            (COPILOT_INTELLIJ / "global-agents-instructions.md",
             AGENTS_MD,                      "file"),
            (COPILOT_INTELLIJ / "global-git-commit-instructions.md",
             INSTRUCTIONS / "GIT_COMMIT.md", "file"),
        ]

    return links

# ── VS Code global settings ───────────────────────────────────────────────────

def wire_vscode(det):
    if not det["copilot_vscode"]:
        return
    bold("Wiring VS Code Copilot...")
    settings = {}
    if VSCODE_SETTINGS.exists():
        try:
            raw   = VSCODE_SETTINGS.read_text(encoding="utf-8")
            clean = re.sub(r"//.*$", "", raw, flags=re.MULTILINE)
            clean = re.sub(r"/\*.*?\*/", "", clean, flags=re.DOTALL)
            settings = json.loads(clean)
        except Exception as exc:
            warn(f"Could not parse settings.json: {exc} — skipping VS Code wiring")
            return
    else:
        VSCODE_SETTINGS.parent.mkdir(parents=True, exist_ok=True)

    settings["github.copilot.chat.codeGeneration.instructions"] = [
        {"file": str(AGENTS_MD)},
        {"file": str(INSTRUCTIONS / "COPILOT.md")},
        {"file": str(INSTRUCTIONS / "VSCODE.md")},
    ]
    settings["github.copilot.chat.commitMessageGeneration.instructions"] = [
        {"file": str(INSTRUCTIONS / "GIT_COMMIT.md")},
    ]
    VSCODE_SETTINGS.write_text(json.dumps(settings, indent=2, ensure_ascii=False), encoding="utf-8")
    ok(str(VSCODE_SETTINGS))

# ── RTK auto-install ──────────────────────────────────────────────────────────

def install_rtk():
    bold("Setting up RTK...")
    # Already installed?
    existing = shutil.which("rtk") or (str(RTK_EXE) if RTK_EXE.exists() else None)
    if existing:
        try:
            r = subprocess.run([existing, "--version"], capture_output=True, text=True)
            if r.returncode == 0:
                ok(f"RTK already installed: {r.stdout.strip()}")
                return existing
        except Exception:
            pass
        info("rtk exists but failed — reinstalling")

    url    = RTK_URLS.get(platform.system())
    is_zip = platform.system() == "Windows"
    if not url:
        warn(f"RTK auto-install not supported on {platform.system()}")
        info("Install manually: https://github.com/rtk-ai/rtk/releases")
        return None

    RTK_BIN_DIR.mkdir(parents=True, exist_ok=True)
    tmp = str(RTK_BIN_DIR / ("dl.zip" if is_zip else "dl.tar.gz"))
    try:
        info("Downloading RTK from GitHub releases...")
        urllib.request.urlretrieve(url, tmp)
        if is_zip:
            with zipfile.ZipFile(tmp, "r") as z:
                z.extractall(str(RTK_BIN_DIR))
        else:
            subprocess.run(["tar", "-xzf", tmp, "-C", str(RTK_BIN_DIR)], check=True)
        Path(tmp).unlink(missing_ok=True)
        if not IS_WIN:
            RTK_EXE.chmod(0o755)
        r = subprocess.run([str(RTK_EXE), "--version"], capture_output=True, text=True)
        if r.returncode == 0:
            ok(f"RTK installed: {r.stdout.strip()}")
            if not shutil.which("rtk"):
                warn(f"Add {RTK_BIN_DIR} to your PATH:")
                if IS_WIN:
                    info(f'  setx PATH "%PATH%;{RTK_BIN_DIR}"')
                else:
                    info(f'  echo \'export PATH="{RTK_BIN_DIR}:$PATH"\' >> ~/.bashrc')
            return str(RTK_EXE)
    except Exception as exc:
        warn(f"RTK download failed: {exc}")
        info("Install manually: https://github.com/rtk-ai/rtk/releases")
    return None


def wire_rtk(rtk_path, det):
    if not rtk_path:
        return
    bold("Wiring RTK hooks...")
    cmds = []
    if det["opencode"]: cmds.append((["--opencode", "--auto-patch"], "opencode"))
    if det["claude"]:   cmds.append((["--auto-patch"],               "claude"))
    if det["gemini"]:   cmds.append((["--gemini", "--auto-patch"],   "gemini"))
    if det["codex"]:
        info("rtk/codex: prompt-level — already in instructions/codex-AGENTS.md")
    for flags, label in cmds:
        try:
            subprocess.run([rtk_path, "init", "-g"] + flags, check=True)
            ok(f"rtk/{label}")
        except (subprocess.CalledProcessError, FileNotFoundError) as exc:
            warn(f"rtk/{label} failed: {exc}")
    # Disable telemetry
    try:
        subprocess.run([rtk_path, "telemetry", "disable"], check=True, capture_output=True)
        ok("rtk telemetry disabled")
    except Exception:
        pass

# ── Symlink helpers ───────────────────────────────────────────────────────────

def remove_existing(path):
    if not path.exists() and not path.is_symlink():
        return
    if path.is_symlink() or (IS_WIN and is_junction(path)):
        path.unlink(missing_ok=True)
        return
    bak = path.with_suffix(path.suffix + ".bak")
    info(f"backup {path.name} -> {bak.name}")
    if bak.exists():
        shutil.rmtree(bak) if bak.is_dir() else bak.unlink()
    path.rename(bak)

def is_junction(path):
    try:
        import ctypes
        return bool(ctypes.windll.kernel32.GetFileAttributesW(str(path)) & 0x400)
    except Exception:
        return False

def make_link(link, target, kind):
    link.parent.mkdir(parents=True, exist_ok=True)
    remove_existing(link)
    if IS_WIN and kind == "dir":
        subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(target)],
                       check=True, capture_output=True)
    else:
        link.symlink_to(target, target_is_directory=(kind == "dir"))

def apply_links(links):
    done = skipped = 0
    for link, target, kind in links:
        if not target.exists():
            warn(f"SKIP {link.name} (source missing: {target.relative_to(REPO)})")
            skipped += 1
            continue
        try:
            label = Path("~") / link.relative_to(HOME)
        except ValueError:
            label = link
        try:
            make_link(link, target, kind)
            ok(str(label))
            done += 1
        except Exception as exc:
            warn(f"FAIL {label} ({exc})")
            skipped += 1
    return done, skipped

# ── Git hooks (install per-repo via PATH lookup) ──────────────────────────────

def add_git_template():
    """Wire hooks/ as git's global init.templateDir so every new clone gets them."""
    hooks_src = REPO / "hooks"
    if not hooks_src.exists():
        return
    try:
        subprocess.run(
            ["git", "config", "--global", "init.templateDir", str(hooks_src)],
            check=True, capture_output=True
        )
        ok(f"git init.templateDir -> {hooks_src}")
        info("Git hooks will be installed in every new clone automatically")
        info("For existing repos: cd your-repo && git init  (safe, just refreshes hooks)")
    except Exception as exc:
        warn(f"Could not set git templateDir: {exc}")

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print()
    bold("ai-framework setup")
    bold("=" * 44)
    info(f"repo: {REPO}")
    print()

    det = detect()
    bold("Detected tools:")
    labels = {
        "opencode":         "OpenCode          [PRIMARY]",
        "claude":           "Claude Code",
        "codex":            "Codex CLI",
        "gemini":           "Gemini CLI",
        "copilot_intellij": "Copilot IntelliJ  (Windows)",
        "copilot_vscode":   "Copilot VS Code",
        "rtk":              "RTK",
    }
    for key, label in labels.items():
        found  = det.get(key, False)
        status = _c("0;32", "found") if found else _c("0;90", "not found")
        print(f"     {label:<34} {status}")
    print()

    # 1. Symlinks
    bold("Wiring symlinks...")
    links = build_links(det)
    done, skipped = apply_links(links)
    print()

    # 2. VS Code global settings
    wire_vscode(det)
    print()

    # 3. Git hooks via templateDir
    bold("Configuring git hooks...")
    add_git_template()
    print()

    # 4. RTK
    rtk_path = shutil.which("rtk") or (str(RTK_EXE) if RTK_EXE.exists() and det["rtk"] else None)
    if not det["rtk"]:
        rtk_path = install_rtk()
    else:
        ok("RTK already installed")
    wire_rtk(rtk_path, det)
    print()

    bold("=" * 44)
    bold(f"Done — {done} links wired, {skipped} skipped.")
    print()
    bold("Open any project folder in OpenCode or VS Code — framework is active.")
    info("To update: cd ai-framework && git pull")
    print()

if __name__ == "__main__":
    main()
