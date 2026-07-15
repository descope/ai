
#!/bin/bash
# ─────────────────────────────────────────────────────────────
# Descope MCP Server Wrapper for Claude Code
# ─────────────────────────────────────────────────────────────
#
# Claude Code's PreToolUse hooks cannot inject headers into MCP
# requests. This wrapper bridges that gap:
#
#   1. Claude Code launches this as a command-type MCP server
#   2. It reads JSON-RPC messages from stdin
#   3. Reads the latest token from the hook's cache
#   4. Forwards requests to upstream with Authorization header
#   5. Pipes responses back to Claude Code on stdout
#
# The PreToolUse hook (descope-auth-cc.sh) runs BEFORE this
# wrapper receives each tool call, ensuring the cache is fresh.
#
# Usage (in .claude/settings.json):
#   "github": {
#     "command": "hooks/descope-mcp-wrapper.sh",
#     "args": ["https://mcp.github.com/sse"],
#     "env": { "DESCOPE_SERVER_KEY": "github" }
#   }
#
# ─────────────────────────────────────────────────────────────

set -e

HOOKS_DIR="$(cd "$(dirname "$0")" && pwd)"
TOKEN_DIR="${HOOKS_DIR}/.token-cache"
LOG_FILE="${HOOKS_DIR}/descope-auth.log"

UPSTREAM_URL="${1:?Usage: descope-mcp-wrapper.sh <upstream-mcp-url>}"
SERVER_KEY="${DESCOPE_SERVER_KEY:?Set DESCOPE_SERVER_KEY env var}"

log() {
  echo "[mcp-wrapper] $(date -u +%Y-%m-%dT%H:%M:%SZ) $*" >> "$LOG_FILE" 2>&1
}

get_token() {
  local cache_file="${TOKEN_DIR}/${SERVER_KEY}.json"
  if [ -f "$cache_file" ]; then
    jq -r '.access_token // empty' "$cache_file" 2>/dev/null
  fi
}

log "Starting wrapper: ${SERVER_KEY} → ${UPSTREAM_URL}"

while IFS= read -r LINE; do
  [ -z "$LINE" ] && continue

  if ! echo "$LINE" | jq empty 2>/dev/null; then
    log "WARN: Non-JSON input: ${LINE:0:100}"
    continue
  fi

  TOKEN=$(get_token)

  if [ -z "$TOKEN" ]; then
    MSG_ID=$(echo "$LINE" | jq -r '.id // null')
    echo "{\"jsonrpc\":\"2.0\",\"id\":${MSG_ID},\"error\":{\"code\":-32000,\"message\":\"No Descope auth token available for ${SERVER_KEY}. Ensure the PreToolUse hook ran.\"}}"
    log "ERROR: No token in cache for ${SERVER_KEY}"
    continue
  fi

  RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$UPSTREAM_URL" \
    -H "Content-Type: application/json" \
    -H "Accept: application/json" \
    -H "Authorization: Bearer ${TOKEN}" \
    -d "$LINE" 2>/dev/null)

  HTTP_CODE=$(echo "$RESPONSE" | tail -1)
  BODY=$(echo "$RESPONSE" | sed '$d')

  if [ "$HTTP_CODE" -ge 200 ] && [ "$HTTP_CODE" -lt 300 ]; then
    echo "$BODY"
  else
    MSG_ID=$(echo "$LINE" | jq -r '.id // null')
    ESCAPED_BODY=$(echo "$BODY" | jq -Rs '.' 2>/dev/null || echo "\"upstream error\"")
    echo "{\"jsonrpc\":\"2.0\",\"id\":${MSG_ID},\"error\":{\"code\":-32000,\"message\":\"Upstream MCP error ${HTTP_CODE}\",\"data\":${ESCAPED_BODY}}}"
    log "ERROR: Upstream returned ${HTTP_CODE}: ${BODY:0:200}"
  fi

done

log "Wrapper stdin closed, exiting"