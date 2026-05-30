#!/usr/bin/env bash
# ============================================================
# AI Framework Installer
# ============================================================
# Usage:
#   Project-level (recommended):
#     curl -fsSL https://raw.githubusercontent.com/your-org/your-framework/main/install.sh | bash
#
#   Project-level from local clone:
#     bash install.sh
#
#   Global (available across all projects on this machine):
#     bash install.sh --global
#
# What it does:
#   - Copies .opencode/agents/ and .opencode/skills/ into the workspace
#   - Copies AGENTS.md, workflow-guide.md, Manual.md, _opencode.json
#   - Replaces [XXX] in _opencode.json with your project folder name
#   - Prints a checklist of what to do next
# ============================================================

set -euo pipefail

# ── Colors ──────────────────────────────────────────────────
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
BOLD='\033[1m'
RESET='\033[0m'

ok()   { echo -e "${GREEN}✅ $1${RESET}"; }
warn() { echo -e "${YELLOW}⚠️  $1${RESET}"; }
err()  { echo -e "${RED}❌ $1${RESET}"; exit 1; }
info() { echo -e "${CYAN}$1${RESET}"; }
bold() { echo -e "${BOLD}$1${RESET}"; }

# ── Arguments ────────────────────────────────────────────────
GLOBAL=false
for arg in "$@"; do
  case $arg in
    --global) GLOBAL=true ;;
    --help|-h)
      echo "Usage: bash install.sh [--global]"
      echo ""
      echo "  (no flag)  Install into current directory (recommended)"
      echo "  --global   Install into ~/.config/opencode/ for all projects"
      exit 0
      ;;
  esac
done

# ── Locate framework source ──────────────────────────────────
# Works whether run via curl | bash or from a local clone
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-/dev/stdin}")" 2>/dev/null && pwd || pwd)"

# If piped from curl, SCRIPT_DIR will be /dev/fd or similar — detect this
if [ ! -f "$SCRIPT_DIR/_opencode.json" ]; then
  # Try to find framework files relative to a temp clone
  FRAMEWORK_REPO="https://github.com/your-org/your-framework.git"
  TEMP_DIR=$(mktemp -d)
  info "Cloning framework into temp directory..."
  git clone --depth 1 "$FRAMEWORK_REPO" "$TEMP_DIR" 2>/dev/null || \
    err "Could not clone framework. Run from a local clone instead: bash install.sh"
  SCRIPT_DIR="$TEMP_DIR"
  CLEANUP_TEMP=true
else
  CLEANUP_TEMP=false
fi

# ── Detect target directory ───────────────────────────────────
if $GLOBAL; then
  TARGET_DIR="$HOME/.config/opencode"
  mkdir -p "$TARGET_DIR"
  PROJECT_NAME="global"
  info ""
  bold "Installing globally into $TARGET_DIR"
  warn "Global install means all projects share these agents and skills."
  warn "Project-level _opencode.json still needs [XXX] replaced manually per project."
  info ""
else
  TARGET_DIR="$(pwd)"
  PROJECT_NAME="$(basename "$TARGET_DIR")"
  info ""
  bold "Installing into: $TARGET_DIR"
  info "Detected project name: ${PROJECT_NAME}"
  info ""
fi

# ── Confirm ───────────────────────────────────────────────────
read -r -p "$(echo -e "${BOLD}Proceed? [Y/n]: ${RESET}")" confirm
confirm="${confirm:-Y}"
if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
  echo "Aborted."
  exit 0
fi

echo ""

# ── Copy framework files ──────────────────────────────────────
copy_file() {
  local src="$1"
  local dst="$2"
  local label="$3"
  if [ -f "$src" ]; then
    mkdir -p "$(dirname "$dst")"
    cp "$src" "$dst"
    ok "$label"
  else
    warn "Not found, skipping: $src"
  fi
}

copy_dir() {
  local src="$1"
  local dst="$2"
  local label="$3"
  if [ -d "$src" ]; then
    mkdir -p "$dst"
    cp -r "$src/." "$dst/"
    ok "$label"
  else
    warn "Not found, skipping: $src"
  fi
}

bold "Copying framework files..."
echo ""

copy_file "$SCRIPT_DIR/AGENTS.md"          "$TARGET_DIR/AGENTS.md"          "AGENTS.md"
copy_file "$SCRIPT_DIR/workflow-guide.md"  "$TARGET_DIR/workflow-guide.md"  "workflow-guide.md"
copy_file "$SCRIPT_DIR/Manual.md"          "$TARGET_DIR/Manual.md"          "Manual.md"
copy_file "$SCRIPT_DIR/_opencode.json"     "$TARGET_DIR/_opencode.json"     "_opencode.json"

mkdir -p "$TARGET_DIR/docs"
copy_file "$SCRIPT_DIR/docs/refactoring-plan.md" \
          "$TARGET_DIR/docs/refactoring-plan.md"  "docs/refactoring-plan.md"

copy_dir "$SCRIPT_DIR/.opencode/agents" \
         "$TARGET_DIR/.opencode/agents"  ".opencode/agents/ ($(ls "$SCRIPT_DIR/.opencode/agents/" | wc -l | tr -d ' ') agents)"

copy_dir "$SCRIPT_DIR/.opencode/skills" \
         "$TARGET_DIR/.opencode/skills"  ".opencode/skills/ ($(ls "$SCRIPT_DIR/.opencode/skills/" | wc -l | tr -d ' ') skills)"

# ── Replace [XXX] placeholder ─────────────────────────────────
if ! $GLOBAL; then
  CONFIG_FILE="$TARGET_DIR/_opencode.json"
  if [ -f "$CONFIG_FILE" ] && grep -q "\[XXX\]" "$CONFIG_FILE"; then
    echo ""
    bold "Replacing [XXX] with '${PROJECT_NAME}' in _opencode.json..."
    if [[ "$OSTYPE" == "darwin"* ]]; then
      sed -i '' "s/\[XXX\]/${PROJECT_NAME}/g" "$CONFIG_FILE"
    else
      sed -i "s/\[XXX\]/${PROJECT_NAME}/g" "$CONFIG_FILE"
    fi
    ok "[XXX] → ${PROJECT_NAME}"
  fi
fi

# ── Install git hooks ─────────────────────────────────────────
echo ""
bold "Git hooks setup..."
HOOKS_FOUND=false

find "$TARGET_DIR" -maxdepth 2 -name ".git" -type d | while read -r gitdir; do
  REPO_DIR="$(dirname "$gitdir")"
  REPO_NAME="$(basename "$REPO_DIR")"
  if [ -f "$SCRIPT_DIR/.opencode/skills/git-hooks/scripts/install-hooks.sh" ]; then
    cp -r "$SCRIPT_DIR/.opencode/skills/git-hooks/scripts" "$REPO_DIR/scripts/hooks" 2>/dev/null || true
    bash "$REPO_DIR/scripts/hooks/install-hooks.sh" 2>/dev/null && \
      ok "Git hooks installed in $REPO_NAME" || \
      warn "Could not auto-install hooks in $REPO_NAME — run manually: bash scripts/hooks/install-hooks.sh"
    HOOKS_FOUND=true
  fi
done

if ! $HOOKS_FOUND; then
  warn "No git repos found in subdirectories — install hooks manually in each repo:"
  echo "     bash scripts/hooks/install-hooks.sh"
fi

# ── Cleanup ───────────────────────────────────────────────────
if $CLEANUP_TEMP; then
  rm -rf "$TEMP_DIR"
fi

# ── Done ─────────────────────────────────────────────────────
echo ""
echo "────────────────────────────────────────────────────────"
bold "✅ Framework installed successfully"
echo "────────────────────────────────────────────────────────"
echo ""
bold "Next steps:"
echo ""
echo "  1. Open ${TARGET_DIR} in opencode (not a repo subfolder)"
if ! $GLOBAL; then
  echo "  2. Review _opencode.json — add any additional repo paths"
fi
echo "  3. Start opencode — first-run analysis runs automatically"
echo "  4. Confirm the detected stack and conventions"
echo "  5. Review docs/refactoring-plan.md if generated"
echo ""
bold "Quick checklist:"
echo "  [ ] opencode CLI installed and authenticated"
echo "  [ ] All repos cloned and accessible locally"
echo "  [ ] opencode started from workspace root (not inside a repo)"
if ! $GLOBAL; then
  echo "  [ ] _opencode.json updated with correct repo paths"
fi
echo "  [ ] First-run analysis completed and confirmed"
echo "  [ ] docs/refactoring-plan.md reviewed (if generated)"
echo "  [ ] Git hooks installed in all repos"
echo ""
info "Read workflow-guide.md for day-to-day usage."
echo ""