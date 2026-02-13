
#!/bin/bash
# ─────────────────────────────────────────────────────────────
# Descope Agent Hooks Installer — Cursor
# ─────────────────────────────────────────────────────────────
#
# Usage:
#   curl -fsSL https://agent-hooks.sh/install.sh | bash
#
# Or from the cloned repo:
#   ./install.sh
#
# ─────────────────────────────────────────────────────────────

set -e

HOOKS_DIR="${HOME}/.cursor/hooks"
HOOKS_JSON="${HOME}/.cursor/hooks.json"
REPO_BASE="https://raw.githubusercontent.com/descope/agent-hooks/main"

echo "🔐 Descope Agent Hooks Installer (Cursor)"
echo "───────────────────────────────────────────"

# ─── Check dependencies ─────────────────────────────────────

for cmd in jq curl; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "❌ Required dependency missing: $cmd"
    echo "   Install it and re-run this script."
    exit 1
  fi
done
echo "✓ Dependencies: jq, curl"

# ─── Create hooks directory ─────────────────────────────────

mkdir -p "$HOOKS_DIR"
echo "✓ Hooks directory: $HOOKS_DIR"

# ─── Helper: install a file from repo or local clone ────────

install_file() {
  local repo_path="$1" dest="$2"
  if [ -f "./$repo_path" ]; then
    cp "./$repo_path" "$dest"
  else
    curl -fsSL "${REPO_BASE}/${repo_path}" -o "$dest"
  fi
}

# ─── Install hook script ────────────────────────────────────

install_file "cursor/descope-auth.sh" "$HOOKS_DIR/descope-auth.sh"
chmod +x "$HOOKS_DIR/descope-auth.sh"
echo "✓ Hook script installed"

# ─── Install example config ─────────────────────────────────

CONFIG_FILE="$HOOKS_DIR/descope-auth.config.json"
if [ -f "$CONFIG_FILE" ]; then
  echo "⚠ Config already exists at $CONFIG_FILE — skipping"
else
  install_file "cursor/descope-auth.config.example.json" "$CONFIG_FILE"
  echo "✓ Example config installed (edit with your Descope credentials)"
fi

# ─── Register hook in hooks.json ─────────────────────────────

if [ -f "$HOOKS_JSON" ]; then
  if jq -e '.hooks.beforeMCPExecution[]? | select(.command == "./hooks/descope-auth.sh")' "$HOOKS_JSON" >/dev/null 2>&1; then
    echo "✓ Hook already registered in hooks.json"
  else
    UPDATED=$(jq '.hooks.beforeMCPExecution = (.hooks.beforeMCPExecution // []) + [{"command": "./hooks/descope-auth.sh"}]' "$HOOKS_JSON")
    echo "$UPDATED" > "$HOOKS_JSON"
    echo "✓ Hook added to existing hooks.json"
  fi
else
  install_file "cursor/hooks.json" "$HOOKS_JSON"
  echo "✓ Created hooks.json"
fi

# ─── Done ────────────────────────────────────────────────────

echo ""
echo "───────────────────────────────────────────"
echo "✅ Descope Agent Hooks installed for Cursor!"
echo ""
echo "Next steps:"
echo "  1. Edit $CONFIG_FILE"
echo "     with your Descope project ID, client credentials,"
echo "     and MCP server audience values."
echo ""
echo "  2. Restart Cursor to activate the hooks."
echo ""
echo "  3. MCP tool calls will now automatically acquire"
echo "     scoped tokens from Descope before execution."
echo ""
echo "Docs: https://agent-hooks.sh"
echo "───────────────────────────────────────────"
