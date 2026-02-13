
#!/bin/bash
# ─────────────────────────────────────────────────────────────
# Descope Agent Hooks Installer — Claude Code
# ─────────────────────────────────────────────────────────────
#
# Usage:
#   curl -fsSL https://agent-hooks.sh/install-claude-code.sh | bash
#
# Or from the cloned repo:
#   ./install-claude-code.sh
#
# Installs into the CURRENT PROJECT directory by default.
# Pass --global to install to ~/.claude/ instead.
#
# ─────────────────────────────────────────────────────────────

set -e

GLOBAL=false
if [ "$1" = "--global" ]; then
  GLOBAL=true
fi

if [ "$GLOBAL" = true ]; then
  SETTINGS_DIR="${HOME}/.claude"
  HOOKS_DIR="${HOME}/.claude/hooks"
else
  SETTINGS_DIR=".claude"
  HOOKS_DIR="hooks"
fi

SETTINGS_FILE="${SETTINGS_DIR}/settings.json"
REPO_BASE="https://raw.githubusercontent.com/descope/agent-hooks/main"

echo "🔐 Descope Agent Hooks Installer (Claude Code)"
echo "────────────────────────────────────────────────"
if [ "$GLOBAL" = true ]; then
  echo "Mode: Global (~/.claude)"
else
  echo "Mode: Project (.claude)"
fi

# ─── Check dependencies ─────────────────────────────────────

for cmd in jq curl; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "❌ Required: $cmd"
    exit 1
  fi
done
echo "✓ Dependencies: jq, curl"

# ─── Create directories ─────────────────────────────────────

mkdir -p "$SETTINGS_DIR"
mkdir -p "$HOOKS_DIR"
echo "✓ Directories created"

# ─── Helper: install a file from repo or local clone ────────

install_file() {
  local repo_path="$1" dest="$2"
  if [ -f "./$repo_path" ]; then
    cp "./$repo_path" "$dest"
  else
    curl -fsSL "${REPO_BASE}/${repo_path}" -o "$dest"
  fi
}

# ─── Install hook scripts ───────────────────────────────────

install_file "claude-code/descope-auth-cc.sh" "${HOOKS_DIR}/descope-auth-cc.sh"
install_file "claude-code/descope-mcp-wrapper.sh" "${HOOKS_DIR}/descope-mcp-wrapper.sh"
chmod +x "${HOOKS_DIR}/descope-auth-cc.sh"
chmod +x "${HOOKS_DIR}/descope-mcp-wrapper.sh"
echo "✓ Hook scripts installed"

# ─── Install config ─────────────────────────────────────────

CONFIG_FILE="${HOOKS_DIR}/descope-auth.config.json"
if [ -f "$CONFIG_FILE" ]; then
  echo "⚠ Config already exists — skipping"
else
  install_file "claude-code/descope-auth.config.example.json" "$CONFIG_FILE"
  echo "✓ Example config installed"
fi

# ─── Update settings.json ───────────────────────────────────

if [ -f "$SETTINGS_FILE" ]; then
  if jq -e '.hooks.PreToolUse[]?.hooks[]? | select(.command == "hooks/descope-auth-cc.sh")' "$SETTINGS_FILE" >/dev/null 2>&1; then
    echo "✓ Hook already registered in settings.json"
  else
    UPDATED=$(jq '
      .hooks = (.hooks // {}) |
      .hooks.PreToolUse = (.hooks.PreToolUse // []) + [{
        "matcher": "^mcp__",
        "hooks": [{"type": "command", "command": "hooks/descope-auth-cc.sh"}]
      }]
    ' "$SETTINGS_FILE")
    echo "$UPDATED" > "$SETTINGS_FILE"
    echo "✓ Hook added to existing settings.json"
  fi
else
  install_file "claude-code/settings.json" "$SETTINGS_FILE"
  echo "✓ Created settings.json"
fi

# ─── Done ────────────────────────────────────────────────────

echo ""
echo "────────────────────────────────────────────────"
echo "✅ Descope Agent Hooks installed for Claude Code!"
echo ""
echo "Next steps:"
echo "  1. Edit ${CONFIG_FILE}"
echo "     with your Descope credentials and MCP server config."
echo ""
echo "  2. Add MCP servers to ${SETTINGS_FILE}:"
echo "     \"mcpServers\": {"
echo "       \"github\": {"
echo "         \"command\": \"hooks/descope-mcp-wrapper.sh\","
echo "         \"args\": [\"https://mcp.github.com/sse\"],"
echo "         \"env\": { \"DESCOPE_SERVER_KEY\": \"github\" }"
echo "       }"
echo "     }"
echo ""
echo "  3. Run: claude"
echo "     Hooks activate automatically on MCP tool calls."
echo ""
echo "Docs: https://agent-hooks.sh"
echo "────────────────────────────────────────────────"
