#!/bin/sh
# install-hooks.sh: installs git hooks for this repo
# Run from the repo root after cloning
HOOKS_DIR=".git/hooks"
SCRIPTS_DIR="scripts/hooks"
if [ ! -d "$HOOKS_DIR" ]; then
  echo "❌ Not a git repository. Run from the repo root."
  exit 1
fi
echo "Installing git hooks..."
for hook in pre-commit commit-msg pre-push; do
  if [ -f "$SCRIPTS_DIR/$hook" ]; then
    cp "$SCRIPTS_DIR/$hook" "$HOOKS_DIR/$hook"
    chmod +x "$HOOKS_DIR/$hook"
    echo "  ✅ $hook installed"
  else
    echo "  ⚠️  $hook not found in $SCRIPTS_DIR — skipped"
  fi
done
echo ""
echo "Done. Protected branches: main, master, develop"
