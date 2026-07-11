#!/usr/bin/env python3
"""
ai-framework setup
==================
Run once per machine from the ai-framework folder.
Re-run anytime — stale links are cleaned, broken links are fixed, new tools are detected.

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

def ok(msg):    print(_c("0;32", f"  OK   {msg}"))
def warn(msg):  print(_c("1;33", f"  WARN {msg}"))
def info(msg):  print(_c("0;36", f"       {msg}"))
def bold(msg):  print(_c("1",    msg))
def err(msg):   print(_c("0;31", f"  ERR  {msg}"))
def fail(msg):  print(_c("0;31", f"  FAIL {msg}")); return False

REPO = Path(__file__).resolve().parent
HOME = Path.home()

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
    RTK_CONFIG      = Path(os.environ.get("APPDATA", "")) / "rtk" / "config.toml"
elif platform.system() == "Darwin":
    VSCODE_SETTINGS = HOME / "Library" / "Application Support" / "Code" / "User" / "settings.json"
    RTK_CONFIG      = HOME / "Library" / "Application Support" / "rtk" / "config.toml"
else:
    VSCODE_SETTINGS = HOME / ".config" / "Code" / "User" / "settings.json"
    RTK_CONFIG      = HOME / ".config" / "rtk" / "config.toml"

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

# ── Tool detection ─────────────────────────────────────────────────────────────

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
        "opencode":         bool(shutil.which("opencode") or OPENCODE_DIR.exists()),
        "claude":           bool(shutil.which("claude")   or CLAUDE_DIR.exists()),
        "codex":            bool(shutil.which("codex")    or CODEX_DIR.exists()),
        "gemini":           bool(shutil.which("gemini")   or GEMINI_DIR.exists()),
        "copilot_intellij": IS_WIN and COPILOT_INTELLIJ is not None and COPILOT_INTELLIJ.exists(),
        "copilot_vscode":   bool(shutil.which("code") or VSCODE_SETTINGS.exists()),
        "rtk":              rtk_ok,
    }

# ── Link table ─────────────────────────────────────────────────────────────────

def build_links(det):
    links = []
    if det["opencode"]:
        links += [
            (OPENCODE_DIR / "opencode.json", REPO / "opencode.json", "file"),
            (OPENCODE_DIR / "AGENTS.md",     REPO / "AGENTS.md",     "file"),
            (OPENCODE_DIR / "agents",        AGENTS,                  "dir"),
            (OPENCODE_DIR / "skills",        SKILLS,                  "dir"),
            (OPENCODE_DIR / "commands",      COMMANDS,                "dir"),
            (OPENCODE_DIR / "hooks",         HOOKS,                   "dir"),
        ]
    if det["claude"]:
        links += [
            (CLAUDE_DIR / "CLAUDE.md",               INSTRUCTIONS / "CLAUDE.md", "file"),
            (CLAUDE_DIR / "AGENTS.md",               REPO / "AGENTS.md",         "file"),
            (CLAUDE_DIR / "agents",                  AGENTS,                      "dir"),
            (CLAUDE_DIR / "skills",                  SKILLS,                      "dir"),
            (CLAUDE_DIR / "commands",                COMMANDS,                    "dir"),
            (CLAUDE_DIR / "hooks",                   HOOKS,                       "dir"),
            (CLAUDE_DIR / "hooks" / "session-end.js", HOOKS / "session-end.js",  "file"),
        ]
    if det["codex"]:
        links += [(CODEX_DIR / "AGENTS.md", INSTRUCTIONS / "codex-AGENTS.md", "file")]
    if det["gemini"]:
        links += [
            (GEMINI_DIR / "GEMINI.md", INSTRUCTIONS / "GEMINI.md", "file"),
            (GEMINI_DIR / "skills",    SKILLS,                      "dir"),
        ]
    if det["copilot_intellij"] and IS_WIN and COPILOT_INTELLIJ:
        links += [
            (COPILOT_INTELLIJ / "global-copilot-instructions.md",
             INSTRUCTIONS / "COPILOT.md",   "file"),
            (COPILOT_INTELLIJ / "global-agents-instructions.md",
             REPO / "AGENTS.md",             "file"),
            (COPILOT_INTELLIJ / "global-git-commit-instructions.md",
             INSTRUCTIONS / "GIT_COMMIT.md", "file"),
        ]
    return links

# ── Stale link cleanup ─────────────────────────────────────────────────────────

def cleanup_stale(links):
    """Remove symlinks that point into the repo but aren't in the current link table."""
    bold("Checking for stale links...")
    current_targets = {str(t) for _, t, _ in links}
    stale_count = 0

    # Dirs to scan for stale links pointing at this repo
    scan_dirs = [OPENCODE_DIR, CLAUDE_DIR, CODEX_DIR, GEMINI_DIR]
    if IS_WIN and COPILOT_INTELLIJ:
        scan_dirs.append(COPILOT_INTELLIJ)

    for d in scan_dirs:
        if not d.exists():
            continue
        for item in d.iterdir():
            if item.is_symlink():
                target = item.resolve()
                try:
                    target.relative_to(REPO)
                    in_repo = True
                except ValueError:
                    in_repo = False
                if in_repo and str(target) not in current_targets:
                    try:
                        item.unlink()
                        warn(f"removed stale link: {item.relative_to(HOME)}")
                        stale_count += 1
                    except Exception as exc:
                        warn(f"could not remove stale link {item}: {exc}")

    if stale_count == 0:
        ok("No stale links found")
    else:
        ok(f"Removed {stale_count} stale link(s)")

# ── Symlink helpers ────────────────────────────────────────────────────────────

def remove_existing(path):
    if not path.exists() and not path.is_symlink():
        return
    if path.is_symlink() or (IS_WIN and _is_junction(path)):
        path.unlink(missing_ok=True)
        return
    bak = path.with_suffix(path.suffix + ".bak")
    info(f"backing up {path.name} -> {bak.name}")
    if bak.exists():
        shutil.rmtree(bak) if bak.is_dir() else bak.unlink()
    path.rename(bak)

def _is_junction(path):
    try:
        import ctypes
        return bool(ctypes.windll.kernel32.GetFileAttributesW(str(path)) & 0x400)
    except Exception:
        return False

def _can_symlink_files():
    """Test whether file symlinks are allowed on this system."""
    test_src = REPO / ".symlink-test-src"
    test_lnk = REPO / ".symlink-test-lnk"
    try:
        test_src.write_text("x")
        test_lnk.symlink_to(test_src)
        return True
    except OSError:
        return False
    finally:
        test_src.unlink(missing_ok=True)
        test_lnk.unlink(missing_ok=True)

def _enable_developer_mode_windows():
    """Enable Windows Developer Mode via helper .ps1 + UAC elevation.
    Allows file symlinks without running setup.py as admin permanently.
    """
    if not IS_WIN:
        return True

    import winreg
    _REG = "SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\AppModelUnlock"
    _KEY = "AllowDevelopmentWithoutDevLicense"

    def _read():
        try:
            k = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, _REG)
            v, _ = winreg.QueryValueEx(k, _KEY)
            winreg.CloseKey(k)
            return v == 1
        except Exception:
            return False

    def _write_direct():
        k = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE, _REG, 0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(k, _KEY, 0, winreg.REG_DWORD, 1)
        winreg.CloseKey(k)

    if _read():
        ok("Windows Developer Mode already enabled")
        return True

    bold("Enabling Windows Developer Mode (required for file symlinks)...")

    # Attempt 1: direct write (works if already running as admin)
    try:
        _write_direct()
        if _read():
            ok("Developer Mode enabled")
            return True
    except PermissionError:
        pass
    except Exception as exc:
        warn(f"Direct registry write failed: {exc}")

    # Attempt 2: run helper .ps1 via UAC elevation
    helper = str(REPO / "enable-dev-mode.ps1")
    info("Requesting UAC elevation to enable Developer Mode...")
    info("A UAC prompt will appear — click Yes to continue.")
    try:
        # Build the PowerShell RunAs command from parts to avoid escaping issues
        ps_file_arg = "-NoProfile -ExecutionPolicy Bypass -File " + helper
        ps_command  = " ".join([
            "Start-Process powershell",
            "-Verb RunAs",
            "-Wait",
            "-ArgumentList",
            "'" + ps_file_arg + "'",
        ])
        subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_command],
            capture_output=True, text=True, timeout=60
        )
        if _read():
            ok("Developer Mode enabled via UAC elevation")
            return True
        warn("UAC ran but Developer Mode is still not enabled")
        warn("Enable manually: Settings -> System -> For developers -> Developer Mode -> ON")
        warn("Then re-run setup.py")
        return False
    except subprocess.TimeoutExpired:
        warn("UAC prompt timed out")
        warn("Enable manually: Settings -> System -> For developers -> Developer Mode -> ON")
        return False
    except Exception as exc:
        warn(f"Elevation failed: {exc}")
        warn("Enable manually: Settings -> System -> For developers -> Developer Mode -> ON")
        return False


_FILE_SYMLINK_OK = None  # cached after first check

def make_link(link, target, kind):
    global _FILE_SYMLINK_OK
    link.parent.mkdir(parents=True, exist_ok=True)
    remove_existing(link)

    if IS_WIN and kind == "dir":
        # Directory junctions work without Developer Mode or admin
        subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(target)],
                       check=True, capture_output=True)
        return

    if IS_WIN and kind == "file":
        # File symlinks need Developer Mode or admin — test once and fallback if not available
        if _FILE_SYMLINK_OK is None:
            _FILE_SYMLINK_OK = _can_symlink_files()
        if not _FILE_SYMLINK_OK:
            # Fallback: copy the file instead
            shutil.copy2(target, link)
            info(f"copied (no symlink privilege): {link.name}")
            info("  To use symlinks: Settings -> System -> For developers -> Developer Mode -> ON")
            return

    link.symlink_to(target, target_is_directory=(kind == "dir"))

# ── Apply links with verification ─────────────────────────────────────────────

def apply_links(links):
    """Create all links then verify every one resolves correctly."""
    errors   = []
    warnings = []
    done     = 0

    # Phase 1 — create
    bold("Wiring symlinks...")
    for link, target, kind in links:
        if not target.exists():
            warnings.append(f"source missing — skipped: {target.relative_to(REPO)}")
            warn(f"SKIP {link.name} (source missing: {target.relative_to(REPO)})")
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
            msg = f"{label} -> {target.relative_to(REPO)}: {exc}"
            errors.append(msg)
            err(f"FAIL {label} ({exc})")

    # Phase 2 — verify every created link resolves
    print()
    bold("Verifying links...")
    for link, target, kind in links:
        if not link.exists() and not link.is_symlink():
            continue  # was skipped
        try:
            label = Path("~") / link.relative_to(HOME)
        except ValueError:
            label = link

        if link.is_symlink():
            resolved = link.resolve()
            if not resolved.exists():
                msg = f"broken symlink: {label} -> {resolved} (does not exist)"
                errors.append(msg)
                err(f"BROKEN {label}")
            elif kind == "file" and not resolved.is_file():
                msg = f"wrong type: {label} resolves to a directory, expected file"
                errors.append(msg)
                err(f"WRONG TYPE {label}")
            elif kind == "dir" and not resolved.is_dir():
                msg = f"wrong type: {label} resolves to a file, expected directory"
                errors.append(msg)
                err(f"WRONG TYPE {label}")
            else:
                ok(f"verified: {label}")
        elif link.exists():
            # Copied file (fallback on Windows without symlink privilege) — verify content matches
            if kind == "file":
                src_size  = target.stat().st_size  if target.exists() else -1
                link_size = link.stat().st_size
                if src_size != link_size:
                    msg = f"copied file size mismatch: {label} ({link_size}B vs source {src_size}B)"
                    warnings.append(msg)
                    warn(f"SIZE MISMATCH {label} — re-run setup.py to refresh")
                else:
                    ok(f"verified (copy): {label}")
            else:
                ok(f"verified (junction): {label}")
        else:
            msg = f"missing after wiring: {label}"
            errors.append(msg)
            err(f"MISSING {label}")

    return done, errors, warnings

# ── Verification summary ───────────────────────────────────────────────────────

def print_verification_summary(errors, warnings):
    print()
    if errors:
        bold(_c("0;31", f"=== {len(errors)} ERROR(S) — action required ==="))
        for e in errors:
            err(e)
        print()
        info("Common fixes:")
        info("  Broken symlink  → re-run setup.py (source file may have moved)")
        info("  Permission denied → on Windows, enable Developer Mode or run as admin")
        info("  Wrong type      → manually delete the stale file and re-run setup.py")
    else:
        bold(_c("0;32", "=== All links verified OK ==="))

    if warnings:
        print()
        bold(f"  {len(warnings)} warning(s):")
        for w in warnings:
            warn(f"  {w}")

    return len(errors) == 0

# ── RTK config ─────────────────────────────────────────────────────────────────

RTK_CONFIG_CONTENT = """\
# RTK configuration — ai-framework
# Full reference: https://www.rtk-ai.app/docs/getting-started/configuration/

[tracking]
enabled      = true
history_days = 90       # keep 90 days of token history

[display]
colors    = true
emoji     = true
max_width = 120

[filters]
# Directories excluded from file-reading commands (ls, find, grep, cat).
# Keeps noise low — agent never sees these in output.
ignore_dirs  = [".git", "node_modules", "target", "__pycache__", ".venv", "vendor", "dist", "build", ".next", ".turbo"]
ignore_files = ["*.lock", "*.min.js", "*.min.css", "*.map", "*.snap"]

[tee]
# When a command fails, RTK saves full raw output so the agent can read it
# without re-running the command. Critical for large test suites.
enabled   = true
mode      = "failures"  # "failures" | "always" | "never"
max_files = 30          # keep last 30 failure logs

[telemetry]
enabled = false         # disabled — consistent with isolated-environment rule

[hooks]
# Commands that should NEVER be rewritten by RTK.
# git operations managed by the framework's own guard (Check 2 + Check 4).
# docker exec and psql produce output that should not be filtered.
exclude_commands = [
  "git rebase",
  "git cherry-pick",
  "git bisect",
  "docker exec",
  "psql",
  "mysql",
]
"""

def configure_rtk():
    bold("Configuring RTK...")
    if RTK_CONFIG.exists():
        ok(f"RTK config already exists: {RTK_CONFIG}")
        info("Edit manually to customise: https://www.rtk-ai.app/docs/getting-started/configuration/")
        return True
    try:
        RTK_CONFIG.parent.mkdir(parents=True, exist_ok=True)
        RTK_CONFIG.write_text(RTK_CONFIG_CONTENT, encoding="utf-8")
        ok(f"RTK config created: {RTK_CONFIG}")
        info("  telemetry disabled (isolated-environment rule)")
        info("  git operations excluded from auto-rewrite")
        info("  90-day token history, 30 failure logs retained")
        return True
    except Exception as exc:
        warn(f"Could not write RTK config: {exc}")
        return False

# ── RTK install ────────────────────────────────────────────────────────────────

def install_rtk():
    bold("Setting up RTK...")
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

# ── VS Code global settings ────────────────────────────────────────────────────

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
        {"file": str(REPO / "AGENTS.md")},
        {"file": str(INSTRUCTIONS / "COPILOT.md")},
        {"file": str(INSTRUCTIONS / "VSCODE.md")},
    ]
    settings["github.copilot.chat.commitMessageGeneration.instructions"] = [
        {"file": str(INSTRUCTIONS / "GIT_COMMIT.md")},
    ]
    VSCODE_SETTINGS.write_text(json.dumps(settings, indent=2, ensure_ascii=False), encoding="utf-8")
    ok(str(VSCODE_SETTINGS))

# ── Git template dir ───────────────────────────────────────────────────────────

def add_git_template():
    bold("Configuring git hooks...")
    hooks_src = REPO / "hooks"
    if not hooks_src.exists():
        warn("hooks/ directory not found — skipping git template")
        return
    template_dir = REPO / "git-template"
    try:
        template_dir.mkdir(parents=True, exist_ok=True)
        (template_dir / "hooks").mkdir(parents=True, exist_ok=True)
        subprocess.run(
            ["git", "config", "--global", "init.templateDir", str(template_dir)],
            check=True, capture_output=True
        )
        ok(f"git init.templateDir -> {template_dir}")
        info("Git hooks will apply to every new clone automatically")
        info("For existing repos: cd your-repo && git init  (safe, just refreshes hooks)")
    except Exception as exc:
        warn(f"Could not set git templateDir: {exc}")

# ── Headroom ───────────────────────────────────────────────────────────────────

def install_headroom():
    bold("Setting up Headroom...")
    if shutil.which("headroom"):
        try:
            r = subprocess.run(["headroom", "--version"], capture_output=True, text=True)
            if r.returncode == 0:
                ok(f"Headroom already installed: {r.stdout.strip()}")
                return True
        except Exception:
            pass
    pip = shutil.which("pip3") or shutil.which("pip")
    if not pip:
        warn("pip not found — cannot install Headroom")
        info("Install manually: pip install headroom-ai")
        return False
    try:
        subprocess.run([pip, "install", "headroom-ai", "--quiet"], check=True)
        ok("Headroom installed")
        return True
    except Exception as exc:
        warn(f"Headroom install failed: {exc}")
        return False

def wire_headroom(det):
    if not shutil.which("headroom"):
        return
    bold("Wiring Headroom...")
    for tool in ["opencode", "claude", "gemini", "codex"]:
        if not det.get(tool):
            continue
        try:
            subprocess.run(["headroom", "wrap", tool], check=True)
            ok(f"headroom/{tool}")
        except (subprocess.CalledProcessError, FileNotFoundError) as exc:
            warn(f"headroom/{tool} failed: {exc}")

# ── Token Optimizer ────────────────────────────────────────────────────────────

TOKEN_OPTIMIZER_REPO = "https://github.com/alexgreensh/token-optimizer.git"

def install_token_optimizer(det):
    bold("Setting up Token Optimizer...")
    git_bin = shutil.which("git")
    if not git_bin:
        warn("git not found — cannot install Token Optimizer")
        return
    if det.get("claude"):
        install_dir = CLAUDE_DIR / "token-optimizer"
        if install_dir.exists():
            ok("token-optimizer/claude already installed")
        else:
            try:
                subprocess.run([git_bin, "clone", "--depth", "1", TOKEN_OPTIMIZER_REPO,
                                str(install_dir)], check=True, capture_output=True)
                install_script = install_dir / "install.sh"
                if install_script.exists() and not IS_WIN:
                    subprocess.run(["bash", str(install_script)], check=True,
                                   cwd=str(install_dir))
                    ok("token-optimizer/claude installed")
                elif IS_WIN:
                    info("token-optimizer: Windows — use Claude Code plugin marketplace")
            except (subprocess.CalledProcessError, FileNotFoundError) as exc:
                warn(f"token-optimizer/claude install failed: {exc}")
    if det.get("opencode"):
        info("token-optimizer/opencode: add 'token-optimizer-opencode' to opencode.json plugins")

def audit_token_optimizer(det):
    if not det.get("claude"):
        return
    install_dir = CLAUDE_DIR / "token-optimizer"
    if not install_dir.exists():
        return
    print()
    info("Token Optimizer installed. Run the one-time audit yourself:")
    info("  In Claude Code: /token-optimizer")

# ── GitHub CLI ─────────────────────────────────────────────────────────────────

def install_gh():
    bold("Setting up GitHub CLI (gh)...")
    if shutil.which("gh"):
        try:
            r = subprocess.run(["gh", "--version"], capture_output=True, text=True)
            if r.returncode == 0:
                ok(f"gh already installed: {r.stdout.splitlines()[0]}")
                return True
        except Exception:
            pass
    system = platform.system()
    if system == "Darwin" and shutil.which("brew"):
        try:
            subprocess.run(["brew", "install", "gh"], check=True)
            ok("gh installed via Homebrew")
            return True
        except Exception as exc:
            warn(f"brew install gh failed: {exc}")
    elif system == "Windows" and shutil.which("winget"):
        try:
            result = subprocess.run(
                ["winget", "install", "--id", "GitHub.cli", "--silent",
                 "--accept-package-agreements", "--accept-source-agreements"],
                capture_output=True, text=True)
            if result.returncode in (0, -1978335189):
                ok("gh installed via winget — restart terminal for PATH")
                return True
        except Exception as exc:
            warn(f"winget install gh failed: {exc}")
    warn("gh not found — install manually: https://cli.github.com")
    info("Required for the commit/push/PR flow (Check 4 in AGENTS.md)")
    return False

# ── Main ───────────────────────────────────────────────────────────────────────

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

    # Build the full link table first (needed for both cleanup and wiring)
    links = build_links(det)

    # 0a. Windows: ensure Developer Mode is enabled so file symlinks work
    if IS_WIN:
        _enable_developer_mode_windows()
        print()

    # 0. Clean stale links from previous installs
    cleanup_stale(links)
    print()

    # 1. Symlinks + verification
    done, errors, warnings = apply_links(links)
    all_ok = print_verification_summary(errors, warnings)
    print()

    # 2. VS Code
    wire_vscode(det)
    print()

    # 3. Git hooks
    add_git_template()
    print()

    # 4. RTK — install, configure, wire
    rtk_path = shutil.which("rtk") or (str(RTK_EXE) if RTK_EXE.exists() and det["rtk"] else None)
    if not det["rtk"]:
        rtk_path = install_rtk()
    else:
        ok("RTK already installed")
    configure_rtk()
    wire_rtk(rtk_path, det)
    print()

    # 5. Headroom
    headroom_ok = install_headroom()
    if headroom_ok:
        wire_headroom(det)
    print()

    # 6. Token Optimizer
    install_token_optimizer(det)
    audit_token_optimizer(det)
    print()

    # 7. GitHub CLI
    install_gh()
    print()

    # Final summary
    bold("=" * 44)
    if all_ok:
        bold(_c("0;32", f"Setup complete — {done} links wired and verified."))
        if IS_WIN and _FILE_SYMLINK_OK is False:
            print()
            warn("File symlinks not available — files were copied instead of linked.")
            warn("After 'git pull', re-run setup.py to refresh copied files.")
            info("To use symlinks permanently: Settings -> System -> For developers -> Developer Mode -> ON")
    else:
        bold(_c("0;31", f"Setup completed with {len(errors)} error(s) — see above."))
        bold(_c("0;31", "Fix the errors and re-run setup.py"))
    print()
    bold("Open any project folder in OpenCode or VS Code — framework is active.")
    info("To update: cd ai-framework && git pull && python setup.py")
    if not all_ok:
        sys.exit(1)
    print()

if __name__ == "__main__":
    main()
