#!/usr/bin/env python3
"""
ai-framework setup
==================
Run once per machine from the ai-framework folder.
Re-run anytime — stale links are cleaned, broken links are fixed, new tools are detected.

    python setup.py

No flags needed. The script detects installed tools automatically.
"""

import hashlib
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

# Single source of truth for the framework version. Bump this and add a
# matching CHANGELOG.md entry together — README and --verify both read this.
FRAMEWORK_VERSION = "1.8.0"

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

ACTION_REQUIRED = []  # (title, [detail lines]) — collected during the run, printed once at the end

def _need_action(title, *detail_lines):
    ACTION_REQUIRED.append((title, list(detail_lines)))

_FILE_SYMLINK_OK = None  # cached after first check
_copy_drift_found = [False]  # mutable cell so apply_links can flag it for the Action Required summary

def _file_hash(path):
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None

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
        # File symlinks need Developer Mode or admin — test once and fallback if not available.
        # We don't attempt to enable it ourselves; see the Action Required summary at the end.
        if _FILE_SYMLINK_OK is None:
            _FILE_SYMLINK_OK = _can_symlink_files()
        if not _FILE_SYMLINK_OK:
            # Fallback: copy the file instead
            shutil.copy2(target, link)
            info(f"copied (no symlink privilege): {link.name}")
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
                if target.exists() and _file_hash(target) != _file_hash(link):
                    msg = f"copied file out of date: {label}"
                    warnings.append(msg)
                    warn(f"OUT OF DATE {label} — re-run setup.py to refresh")
                    _copy_drift_found[0] = True
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

def print_action_required():
    """Print anything the developer needs to do themselves, in one place they can't miss.
    Nothing here blocks setup from finishing — the framework degrades gracefully
    without any of these; this just makes the tradeoff visible instead of silent."""
    print()
    bold("=" * 44)
    if not ACTION_REQUIRED:
        bold(_c("0;32", "Action required — none. Everything checked out."))
        return
    bold(_c("1;33", f"Action required — {len(ACTION_REQUIRED)} item(s)"))
    bold("=" * 44)
    for title, details in ACTION_REQUIRED:
        print()
        warn(title)
        for d in details:
            info(f"  {d}")

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
        template_hooks = template_dir / "hooks"
        template_hooks.mkdir(parents=True, exist_ok=True)
        # Hard-link each hook into the template dir — NOT a symlink, NOT a
        # copy. A hard link is the same inode/bytes as hooks/*, so hooks/
        # stays the single source of truth with zero drift (editing
        # hooks/pre-push updates the template instantly, no re-run of
        # setup.py needed) — but unlike a symlink, git.exe sees it as an
        # ordinary file. That matters because git's init.templateDir
        # recreates whatever it finds in the template dir on the *new*
        # repo: a symlink there means every `git clone`, on every
        # developer's machine, needs Developer Mode/admin AND working
        # symlink support inside git.exe's own MSYS layer — not something
        # we can assume, and it breaks clone with
        # "fatal: cannot symlink ...: Function not implemented" the moment
        # it isn't there. A hard link just gets copied like any other
        # file, so cloning never needs any special privilege.
        # build-verify.sh is linked here too (not in a separate scripts/
        # dir) specifically so it's co-located with pre-push, which finds
        # it via "$(dirname "$0")" at runtime — works in any project,
        # regardless of where ai-framework itself is installed on disk.
        linked = 0
        for hook_name in ("pre-commit", "commit-msg", "pre-push", "build-verify.sh"):
            src = hooks_src / hook_name
            if not src.exists():
                warn(f"hooks/{hook_name} not found — not included in template")
                continue
            dst = template_hooks / hook_name
            remove_existing(dst)
            src.chmod(src.stat().st_mode | 0o111)  # ensure executable at the source
            try:
                os.link(src, dst)  # hard link: same file, zero privilege needed
            except OSError as exc:
                # Cross-device (git-template/ and hooks/ on different
                # volumes) or a filesystem without hard-link support —
                # fall back to a plain copy rather than fail setup.
                shutil.copy2(src, dst)
                info(f"copied (hard link unavailable: {exc.strerror or exc}): {hook_name}")
            linked += 1
        subprocess.run(
            ["git", "config", "--global", "init.templateDir", str(template_dir)],
            check=True, capture_output=True
        )
        ok(f"git init.templateDir -> {template_dir} ({linked} hooks linked)")
        info("Git hooks will apply to every new clone automatically")
        info("For existing repos: cd your-repo && git init  (safe, just refreshes hooks)")
    except Exception as exc:
        warn(f"Could not set git templateDir: {exc}")

def uninstall_git_template():
    """Cleanly undo add_git_template(). Run this — not a manual `rmdir` —
    before deleting or moving the ai-framework folder. `git config
    init.templateDir` is a global, persistent setting: if git-template/ is
    removed but the config still points at it, EVERY future `git clone` or
    `git init` on this machine, on ANY project, prints
      warning: templates not found in <path>
    forever, whether or not that project has anything to do with
    ai-framework. This unsets the config (only if it's still pointing at
    our template dir — never touches it if you've since pointed
    init.templateDir elsewhere) and removes the folder.
    Already-cloned repos are unaffected: their hooks are already sitting
    in their own .git/hooks/, independent of this config.
    """
    bold("Removing git hook template...")
    template_dir = REPO / "git-template"
    current = subprocess.run(
        ["git", "config", "--global", "--get", "init.templateDir"],
        capture_output=True, text=True
    ).stdout.strip()
    if current and Path(current).resolve() == template_dir.resolve():
        subprocess.run(["git", "config", "--global", "--unset", "init.templateDir"], check=True)
        ok("git config --global init.templateDir unset")
    elif current:
        warn(f"init.templateDir points elsewhere ({current}) — left it alone")
    else:
        info("init.templateDir was not set — nothing to unset")
    if template_dir.exists():
        shutil.rmtree(template_dir)
        ok(f"removed {template_dir}")
    else:
        info(f"{template_dir} already gone")
    print()
    info("New `git clone`/`git init` on this machine will no longer install hooks.")
    info("Already-cloned repos keep the hooks they already have.")
    print()

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
                _need_action(
                    "token-optimizer/claude not installed",
                    f"Install manually: git clone {TOKEN_OPTIMIZER_REPO} <path> && bash <path>/install.sh",
                )
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

# ── Token monitoring ─────────────────────────────────────────────────────────
# See monitoring/README.md — ccusage covers cross-tool token/cost dashboards.

def install_ccusage(det):
    """Cross-tool token/cost dashboard — Claude Code, Codex, OpenCode, Gemini CLI,
    Copilot CLI, all in one command. See monitoring/README.md."""
    bold("Checking token/cost dashboard (ccusage)...")
    if shutil.which("ccusage"):
        ok("ccusage already installed")
        return True
    npm = shutil.which("npm")
    if npm:
        try:
            subprocess.run([npm, "install", "-g", "ccusage"],
                           check=True, capture_output=True, timeout=60)
            ok("ccusage installed globally")
            info("  Try: ccusage daily   /   ccusage session   /   ccusage weekly")
            return True
        except Exception as exc:
            warn(f"Global install failed ({exc}) — falls back to npx, no action needed")
    else:
        info("npm not found — that's fine, ccusage runs zero-install via npx")
    info("  Try: npx ccusage@latest daily   (works without any install)")
    return True

# ── Graphify ───────────────────────────────────────────────────────────────────
# Code knowledge graph (tree-sitter AST, zero LLM cost for code) — agents query
# it instead of Read/Glob/grep-ing files to figure out structure. See
# skills/graphify/SKILL.md for the query commands and how it composes with
# zoom-out / first-run-analysis / pattern-enforcement.

def install_graphify():
    bold("Setting up Graphify...")
    if shutil.which("graphify"):
        try:
            r = subprocess.run(["graphify", "--version"], capture_output=True, text=True)
            if r.returncode == 0:
                ok(f"Graphify already installed: {r.stdout.strip()}")
                return True
        except Exception:
            pass
    installer = shutil.which("uv") or shutil.which("pipx")
    if not installer:
        warn("Neither uv nor pipx found — cannot install Graphify")
        _need_action(
            "Graphify not installed",
            "Graphify needs uv or pipx. Install one, then run:",
            "  uv tool install graphifyy   (recommended)",
            "  pipx install graphifyy",
        )
        return False
    try:
        installer_name = Path(installer).name.lower()
        if installer_name in ("uv", "uv.exe"):
            install_result = subprocess.run([installer, "tool", "install", "graphifyy"],
                                             check=True, capture_output=True, text=True)
        else:
            install_result = subprocess.run([installer, "install", "graphifyy"],
                                             check=True, capture_output=True, text=True)

        if shutil.which("graphify"):
            r = subprocess.run(["graphify", "--version"],
                               check=False, capture_output=True, text=True)
            if r.returncode == 0:
                ok("Graphify installed")
                return True

        warn("Graphify installed but could not run after installation")
        # uv installs to a per-user tool dir that isn't always on PATH yet —
        # uv itself usually says so directly. Show it instead of guessing.
        uv_output = (install_result.stdout + install_result.stderr).strip()
        if uv_output:
            info("uv said:")
            for line in uv_output.splitlines():
                info(f"  {line}")
        _need_action(
            "Graphify installed but not runnable",
            "uv installed it, but 'graphify --version' still fails — almost",
            "always a PATH issue (see \"uv said:\" output above, if any).",
            "1. Run 'uv tool update-shell' to register uv's tool bin dir on PATH.",
            "2. A NEW cmd/PowerShell window is often not enough on Windows —",
            "   setx/uv update the registry but an already-running Explorer/shell",
            "   session keeps its old PATH. Log off and back on (or reboot), or",
            "   open System Properties -> Environment Variables -> OK to force a refresh.",
            "3. Confirm the binary directly: run 'uv tool dir --bin' to find it,",
            "   then '<that dir>\\graphify.exe --version' (Windows) to test it in isolation.",
            "4. Once 'graphify --version' works in a fresh shell: re-run 'python setup.py'",
            "   (not just --verify) — this both marks it installed AND registers the",
            "   /graphify skill with each of your assistants (OpenCode, Claude Code, etc).",
        )
        return False
    except subprocess.CalledProcessError as exc:
        warn(f"Graphify install failed: {exc}")
        if exc.stderr:
            info("uv said:")
            for line in exc.stderr.strip().splitlines():
                info(f"  {line}")
        _need_action(
            "Graphify not installed",
            "Install manually: uv tool install graphifyy",
        )
        return False

def wire_graphify(det):
    """Registers Graphify assistants globally. Hook installation is per-project,
    not wired here, so each opened project receives its own rebuild hook."""
    if not shutil.which("graphify"):
        return
    bold("Wiring Graphify...")
    platform_flag = {
        "opencode": "opencode",
        "claude":   None,   # bare `graphify install` targets Claude Code by default
        "codex":    "codex",
        "gemini":   "gemini",
    }
    installed_any = False
    for tool, flag in platform_flag.items():
        if not det.get(tool):
            continue
        try:
            cmd = ["graphify", "install"]
            if flag:
                cmd += ["--platform", flag]
            subprocess.run(cmd, check=True, capture_output=True, cwd=str(REPO))
            ok(f"graphify/{tool}")
            installed_any = True
        except (subprocess.CalledProcessError, FileNotFoundError) as exc:
            warn(f"graphify/{tool} failed: {exc}")
            _need_action(
                f"Graphify not wired for {tool}",
                f"Install manually: graphify install" + (f" --platform {flag}" if flag else ""),
            )
    if not installed_any:
        return
    info("Graphify CLI registration complete (skill available globally).")
    info("Two more steps, run once inside each opened project:")
    info("  cd <project> && graphify <platform> install   # always-on nudge, e.g. opencode/claude/codex/gemini")
    info("  cd <project> && graphify hook install          # keeps graph.json current on commit")
    info("Large repos: use scripts/graphify-smart-viz.sh instead of raw")
    info("`graphify` when HTML output matters — auto-skips viz past ~5000 nodes.")

# ── GitHub CLI ─────────────────────────────────────────────────────────────────

def check_gh():
    """Detect gh only — we don't attempt to install it (package managers may be
    unavailable or restricted). If missing, the framework still works: AGENTS.md
    Check 4 falls back to 'push, then open the PR manually' when gh isn't found."""
    bold("Checking GitHub CLI (gh)...")
    if shutil.which("gh"):
        try:
            r = subprocess.run(["gh", "--version"], capture_output=True, text=True)
            if r.returncode == 0:
                ok(f"gh found: {r.stdout.splitlines()[0]}")
                return True
        except Exception:
            pass
    warn("gh not found")
    _need_action(
        "GitHub CLI (gh) not found",
        "Needed to auto-open PRs at the end of a task.",
        "Without it: the framework still pushes your branch and tells you",
        "to open the PR manually (Check 4 in AGENTS.md) — not blocked, just manual.",
        "Install: https://cli.github.com",
        "Then run: gh auth login",
        "Re-check anytime: python setup.py --verify",
    )
    return False

# ── --verify (read-only) ────────────────────────────────────────────────────────

def verify_only():
    """Read-only health check: no files are written, no links are touched.
    Lets a dev re-check status anytime (e.g. after installing gh, or after IT
    enables Developer Mode) without re-running the full install."""
    print()
    bold("ai-framework verify")
    bold("=" * 44)
    info(f"version: {FRAMEWORK_VERSION}")
    print()

    det = detect()
    links = build_links(det)

    bold("Symlink/copy status:")
    for link, target, kind in links:
        if not link.exists() and not link.is_symlink():
            warn(f"missing: {link.name} — run 'python setup.py' to install")
            continue
        if link.is_symlink() or (IS_WIN and kind == "dir"):
            ok(f"linked: {link.name}")
        elif kind == "file" and target.exists():
            if _file_hash(target) == _file_hash(link):
                ok(f"copy up to date: {link.name}")
            else:
                warn(f"copy out of date: {link.name} — run 'python setup.py' to refresh")
    print()

    check_gh()
    print()

    bold("Graphify status:")
    if shutil.which("graphify"):
        r = subprocess.run(["graphify", "--version"], capture_output=True, text=True)
        if r.returncode == 0:
            ok(f"graphify runnable: {r.stdout.strip()}")
        else:
            warn("graphify found on PATH but 'graphify --version' fails")
            _need_action(
                "Graphify installed but not runnable",
                "Re-run: python setup.py",
            )
    else:
        warn("graphify not found — run 'python setup.py' to install")
        _need_action(
            "Graphify not installed",
            "Run: python setup.py",
        )
    print()

    template_dir = REPO / "git-template"
    current = subprocess.run(
        ["git", "config", "--global", "--get", "init.templateDir"],
        capture_output=True, text=True
    ).stdout.strip()
    if current and Path(current).resolve() == template_dir.resolve() and not template_dir.exists():
        warn(f"git init.templateDir points at {template_dir}, which doesn't exist")
        info("Every 'git clone'/'git init' on this machine warns until this is fixed")
        info("Fix: 'python setup.py' to restore it, or 'python setup.py --uninstall' to remove the config")
    print()

    print_action_required()
    print()

# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    if "--verify" in sys.argv:
        verify_only()
        return
    if "--uninstall" in sys.argv:
        uninstall_git_template()
        return

    print()
    bold("ai-framework setup")
    bold("=" * 44)
    info(f"version: {FRAMEWORK_VERSION}")
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

    # 5. Token Optimizer
    install_token_optimizer(det)
    audit_token_optimizer(det)
    print()

    # 6. Graphify — code knowledge graph (see skills/graphify/SKILL.md)
    if install_graphify():
        wire_graphify(det)
    print()

    # 7. Token monitoring
    install_ccusage(det)
    print()

    # 8. GitHub CLI (detect only — see check_gh docstring)
    check_gh()
    print()

    # Collect the remaining action items that only make sense after wiring
    if IS_WIN and _FILE_SYMLINK_OK is False:
        _need_action(
            "File symlinks not available on this machine",
            "Root config files were copied instead of linked — this is safe,",
            "but they won't auto-update on 'git pull' like the rest of the framework does.",
            "After every 'git pull': re-run 'python setup.py' to refresh them.",
            "To get live-linked files instead: ask IT to enable Developer Mode",
            "(Settings -> System -> For developers), then re-run setup.py.",
        )
    if _copy_drift_found[0]:
        _need_action(
            "Some copied files are out of date",
            "Re-run 'python setup.py' to refresh them (see OUT OF DATE lines above).",
        )

    # Final summary
    bold("=" * 44)
    if all_ok:
        bold(_c("0;32", f"Setup complete — {done} links wired and verified."))
    else:
        bold(_c("0;31", f"Setup completed with {len(errors)} error(s) — see above."))
        bold(_c("0;31", "Fix the errors and re-run setup.py"))
    print()
    bold("Open any project folder in OpenCode or VS Code — framework is active.")
    info("To update: cd ai-framework && git pull && python setup.py")
    info("To re-check tool status without changing anything: python setup.py --verify")

    print_action_required()

    if not all_ok:
        sys.exit(1)
    print()

if __name__ == "__main__":
    main()
