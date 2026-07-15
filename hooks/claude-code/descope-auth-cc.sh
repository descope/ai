
#!/bin/bash
# ─────────────────────────────────────────────────────────────
# Descope Agent Auth Hook for Claude Code
# ─────────────────────────────────────────────────────────────
#
# A PreToolUse hook that acquires a scoped access token from
# Descope before every MCP tool call.
#
# KEY DIFFERENCE FROM CURSOR:
#   Cursor hooks can inject headers directly via
#   {"permission":"allow","headers":{...}}. Claude Code hooks
#   can only allow/block — they cannot modify the request.
#
#   So this hook writes the token to a shared cache file, and
#   the companion MCP wrapper (descope-mcp-wrapper.sh) reads
#   from the cache to inject the Authorization header.
#
# Claude Code stdin:
#   { "tool_name": "mcp__github__create_issue",
#     "tool_input": { ... }, "session_id": "abc123" }
#
# Response:
#   Allow:  exit 0, empty stdout
#   Block:  exit 0, stdout: {"reason": "..."}
#   Error:  exit non-zero
#
# ─────────────────────────────────────────────────────────────

HOOKS_DIR="$(cd "$(dirname "$0")" && pwd)"
CONFIG_FILE="${HOOKS_DIR}/descope-auth.config.json"
LOG_FILE="${HOOKS_DIR}/descope-auth.log"
TOKEN_DIR="${HOOKS_DIR}/.token-cache"

# ─── Logging (stderr only, never stdout) ─────────────────────

log() {
  echo "[descope-auth] $(date -u +%Y-%m-%dT%H:%M:%SZ) $*" >> "$LOG_FILE" 2>&1
}

# ─── Dependency check ────────────────────────────────────────

for cmd in jq curl; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
    log "WARNING: $cmd not found, bypassing auth"
    exit 0
  fi
done

# ─── Read hook input from Claude Code ────────────────────────

INPUT=$(cat)
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // empty')
SESSION_ID=$(echo "$INPUT" | jq -r '.session_id // empty')

log "Hook fired: tool=$TOOL_NAME session=$SESSION_ID"

# ─── Load config ─────────────────────────────────────────────

if [ ! -f "$CONFIG_FILE" ]; then
  log "WARNING: Config not found at $CONFIG_FILE, allowing without auth"
  exit 0
fi

# MCP tool names in Claude Code: mcp__<server>__<tool>
SERVER_NAME=$(echo "$TOOL_NAME" | sed -n 's/^mcp__\([^_]*\)__.*/\1/p')

if [ -z "$SERVER_NAME" ]; then
  log "Not an MCP tool (tool=$TOOL_NAME), allowing"
  exit 0
fi

SERVER_CONFIG=$(jq -c --arg server "$SERVER_NAME" '.servers[$server] // empty' "$CONFIG_FILE" 2>/dev/null)

if [ -z "$SERVER_CONFIG" ] || [ "$SERVER_CONFIG" = "null" ]; then
  SERVER_CONFIG=$(jq -c --arg tool "$TOOL_NAME" '
    .servers | to_entries[] |
    select(.key as $k | $tool | contains($k)) |
    .value
  ' "$CONFIG_FILE" 2>/dev/null | head -1)
fi

if [ -z "$SERVER_CONFIG" ] || [ "$SERVER_CONFIG" = "null" ]; then
  log "No auth config for server=$SERVER_NAME, allowing without auth"
  exit 0
fi

STRATEGY=$(echo "$SERVER_CONFIG" | jq -r '.strategy')
BASE_URL=$(echo "$SERVER_CONFIG" | jq -r '.baseUrl // "https://api.descope.com"')

log "Strategy: $STRATEGY for server=$SERVER_NAME"

# ─── Token cache ─────────────────────────────────────────────

mkdir -p "$TOKEN_DIR"

get_cached_token() {
  local cache_file="${TOKEN_DIR}/${1}.json"
  if [ -f "$cache_file" ]; then
    local expires_at=$(jq -r '.expires_at' "$cache_file" 2>/dev/null)
    local now=$(date +%s)
    local expires_epoch=$(date -d "$expires_at" +%s 2>/dev/null || date -j -f "%Y-%m-%dT%H:%M:%S" "$expires_at" +%s 2>/dev/null || echo 0)
    if [ $((expires_epoch - now)) -gt 30 ]; then
      jq -r '.access_token' "$cache_file"
      return 0
    fi
  fi
  return 1
}

set_cached_token() {
  local cache_file="${TOKEN_DIR}/${1}.json"
  echo "$2" > "$cache_file"
}

# ─── OAuth flows ─────────────────────────────────────────────

do_client_credentials_exchange() {
  local client_id=$(echo "$SERVER_CONFIG" | jq -r '.clientId')
  local client_secret=$(echo "$SERVER_CONFIG" | jq -r '.clientSecret')
  local project_id=$(echo "$SERVER_CONFIG" | jq -r '.projectId')
  local audience=$(echo "$SERVER_CONFIG" | jq -r '.audience')
  local resource=$(echo "$SERVER_CONFIG" | jq -r '.resource // empty')

  local cached=$(get_cached_token "$SERVER_NAME") && { echo "$cached"; return 0; }

  local cc_response=$(curl -s -X POST "${BASE_URL}/oauth2/v1/apps/token" \
    -H "Content-Type: application/json" \
    -d "$(jq -n \
      --arg gt "client_credentials" \
      --arg ci "$client_id" \
      --arg cs "$client_secret" \
      '{grant_type: $gt, client_id: $ci, client_secret: $cs}'
    )")

  local agent_token=$(echo "$cc_response" | jq -r '.access_token // empty')
  if [ -z "$agent_token" ]; then
    log "ERROR: client_credentials failed: $cc_response"
    return 1
  fi

  local te_body=$(jq -n \
    --arg gt "urn:ietf:params:oauth:grant-type:token-exchange" \
    --arg ci "$client_id" \
    --arg cs "$client_secret" \
    --arg st "$agent_token" \
    --arg stt "urn:ietf:params:oauth:token-type:access_token" \
    --arg aud "$audience" \
    --arg res "$resource" \
    '{grant_type: $gt, client_id: $ci, client_secret: $cs,
      subject_token: $st, subject_token_type: $stt, audience: $aud}
     | if $res != "" then . + {resource: $res} else . end')

  local te_response=$(curl -s -X POST "${BASE_URL}/oauth2/v1/apps/${project_id}/token" \
    -H "Content-Type: application/json" \
    -d "$te_body")

  local token=$(echo "$te_response" | jq -r '.access_token // empty')
  if [ -z "$token" ]; then
    log "ERROR: token exchange failed: $te_response"
    return 1
  fi

  local expires_in=$(echo "$te_response" | jq -r '.expires_in // 3600')
  local expires_at=$(date -u -d "+${expires_in} seconds" +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || \
    date -u -v+${expires_in}S +%Y-%m-%dT%H:%M:%SZ 2>/dev/null)

  set_cached_token "$SERVER_NAME" "$(jq -n \
    --arg t "$token" --arg e "$expires_at" \
    '{access_token: $t, expires_at: $e}')"

  echo "$token"
}

do_user_token_exchange() {
  local project_id=$(echo "$SERVER_CONFIG" | jq -r '.projectId')
  local user_token=$(echo "$SERVER_CONFIG" | jq -r '.userAccessToken')
  local audience=$(echo "$SERVER_CONFIG" | jq -r '.audience')
  local resource=$(echo "$SERVER_CONFIG" | jq -r '.resource // empty')

  local cached=$(get_cached_token "$SERVER_NAME") && { echo "$cached"; return 0; }

  local te_body=$(jq -n \
    --arg gt "urn:ietf:params:oauth:grant-type:token-exchange" \
    --arg st "$user_token" \
    --arg stt "urn:ietf:params:oauth:token-type:access_token" \
    --arg aud "$audience" \
    --arg res "$resource" \
    '{grant_type: $gt, subject_token: $st, subject_token_type: $stt, audience: $aud}
     | if $res != "" then . + {resource: $res} else . end')

  local response=$(curl -s -X POST "${BASE_URL}/oauth2/v1/apps/${project_id}/token" \
    -H "Content-Type: application/json" \
    -d "$te_body")

  local token=$(echo "$response" | jq -r '.access_token // empty')
  if [ -z "$token" ]; then
    log "ERROR: user token exchange failed: $response"
    return 1
  fi

  local expires_in=$(echo "$response" | jq -r '.expires_in // 3600')
  local expires_at=$(date -u -d "+${expires_in} seconds" +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || \
    date -u -v+${expires_in}S +%Y-%m-%dT%H:%M:%SZ 2>/dev/null)

  set_cached_token "$SERVER_NAME" "$(jq -n \
    --arg t "$token" --arg e "$expires_at" \
    '{access_token: $t, expires_at: $e}')"

  echo "$token"
}

do_connections() {
  local project_id=$(echo "$SERVER_CONFIG" | jq -r '.projectId')
  local user_token=$(echo "$SERVER_CONFIG" | jq -r '.userAccessToken')
  local app_id=$(echo "$SERVER_CONFIG" | jq -r '.appId')
  local user_id=$(echo "$SERVER_CONFIG" | jq -r '.userId')
  local tenant_id=$(echo "$SERVER_CONFIG" | jq -r '.tenantId // empty')
  local scopes=$(echo "$SERVER_CONFIG" | jq -c '.scopes // []')

  local cached=$(get_cached_token "$SERVER_NAME") && { echo "$cached"; return 0; }

  local body=$(jq -n \
    --arg ai "$app_id" --arg ui "$user_id" --arg ti "$tenant_id" \
    --argjson sc "$scopes" \
    '{appId: $ai, userId: $ui, scopes: $sc}
     | if $ti != "" then . + {tenantId: $ti} else . end')

  local response=$(curl -s -X POST "${BASE_URL}/v1/mgmt/outbound/app/user/token" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer ${project_id}:${user_token}" \
    -d "$body")

  local token=$(echo "$response" | jq -r '.token // .accessToken // .access_token // empty')
  if [ -z "$token" ]; then
    log "ERROR: connections failed: $response"
    return 1
  fi

  local expires_in=$(echo "$response" | jq -r '.expiresIn // .expires_in // 3600')
  local expires_at=$(date -u -d "+${expires_in} seconds" +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || \
    date -u -v+${expires_in}S +%Y-%m-%dT%H:%M:%SZ 2>/dev/null)

  set_cached_token "$SERVER_NAME" "$(jq -n \
    --arg t "$token" --arg e "$expires_at" \
    '{access_token: $t, expires_at: $e}')"

  echo "$token"
}

do_ciba() {
  local client_id=$(echo "$SERVER_CONFIG" | jq -r '.clientId')
  local client_secret=$(echo "$SERVER_CONFIG" | jq -r '.clientSecret')
  local audience=$(echo "$SERVER_CONFIG" | jq -r '.audience')
  local scopes=$(echo "$SERVER_CONFIG" | jq -r '.scopes // empty')
  local login_hint=$(echo "$SERVER_CONFIG" | jq -r '.loginHint // empty')
  local login_hint_token=$(echo "$SERVER_CONFIG" | jq -r '.loginHintToken // empty')
  local binding_message=$(echo "$SERVER_CONFIG" | jq -r '.bindingMessage // empty')
  local poll_interval=$(echo "$SERVER_CONFIG" | jq -r '.pollIntervalSeconds // 2')
  local timeout=$(echo "$SERVER_CONFIG" | jq -r '.timeoutSeconds // 120')

  local auth_body=$(jq -n \
    --arg ci "$client_id" --arg cs "$client_secret" \
    --arg sc "$scopes" --arg aud "$audience" \
    --arg lh "$login_hint" --arg lht "$login_hint_token" \
    --arg bm "$binding_message" \
    '{client_id: $ci, client_secret: $cs, scope: $sc, audience: $aud}
     | if $lh != "" then . + {login_hint: $lh} else . end
     | if $lht != "" then . + {login_hint_token: $lht} else . end
     | if $bm != "" then . + {binding_message: $bm} else . end')

  local auth_response=$(curl -s -X POST "${BASE_URL}/oauth2/v1/apps/bc-authorize" \
    -H "Content-Type: application/json" \
    -d "$auth_body")

  local auth_req_id=$(echo "$auth_response" | jq -r '.auth_req_id // empty')
  if [ -z "$auth_req_id" ]; then
    log "ERROR: CIBA authorize failed: $auth_response"
    return 1
  fi

  local server_interval=$(echo "$auth_response" | jq -r '.interval // empty')
  if [ -n "$server_interval" ] && [ "$server_interval" -gt "$poll_interval" ]; then
    poll_interval=$server_interval
  fi

  log "CIBA: waiting for user consent (polling every ${poll_interval}s)"

  local elapsed=0
  while [ $elapsed -lt $timeout ]; do
    sleep "$poll_interval"
    elapsed=$((elapsed + poll_interval))

    local poll_response=$(curl -s -X POST "${BASE_URL}/oauth2/v1/apps/token" \
      -H "Content-Type: application/json" \
      -d "$(jq -n \
        --arg gt "urn:openid:params:grant-type:ciba" \
        --arg ar "$auth_req_id" \
        --arg ci "$client_id" --arg cs "$client_secret" \
        '{grant_type: $gt, auth_req_id: $ar, client_id: $ci, client_secret: $cs}'
      )")

    local token=$(echo "$poll_response" | jq -r '.access_token // empty')
    if [ -n "$token" ]; then
      log "CIBA: user approved (${elapsed}s)"
      echo "$token"
      return 0
    fi

    local error=$(echo "$poll_response" | jq -r '.error // empty')
    case "$error" in
      authorization_pending) continue ;;
      slow_down) sleep "$poll_interval"; elapsed=$((elapsed + poll_interval)); continue ;;
      *) log "ERROR: CIBA poll failed: $poll_response"; return 1 ;;
    esac
  done

  log "ERROR: CIBA timed out after ${timeout}s"
  return 1
}

# ─── Dispatch ────────────────────────────────────────────────

TOKEN=""
case "$STRATEGY" in
  client_credentials_exchange) TOKEN=$(do_client_credentials_exchange) ;;
  user_token_exchange)         TOKEN=$(do_user_token_exchange) ;;
  connections)                 TOKEN=$(do_connections) ;;
  ciba)                        TOKEN=$(do_ciba) ;;
  *)
    log "ERROR: Unknown strategy: $STRATEGY"
    exit 0
    ;;
esac

# ─── Response to Claude Code ────────────────────────────────

if [ -z "$TOKEN" ]; then
  log "ERROR: Failed to acquire token for server=$SERVER_NAME"
  echo "{\"reason\": \"Descope auth failed: could not acquire token for $SERVER_NAME. Check hooks/descope-auth.log for details.\"}"
  exit 0
fi

log "SUCCESS: Token cached for server=$SERVER_NAME"
exit 0