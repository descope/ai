
#!/bin/bash
# ─────────────────────────────────────────────────────────────
# Descope Agent Auth Hook for Cursor
# ─────────────────────────────────────────────────────────────
#
# A beforeMCPExecution hook that acquires a scoped access token
# from Descope and injects it into the MCP tool call.
#
# Cursor calls this script before every MCP tool execution.
# It receives a JSON payload on stdin with:
#   { email, tool_name, tool_input, model, conversation_id }
#
# The script:
#   1. Reads the tool call context from stdin
#   2. Looks up the auth strategy for this MCP server
#   3. Acquires a scoped token from Descope
#   4. Returns { "permission": "allow", "headers": { "Authorization": "..." } }
#      or { "permission": "deny", "reason": "..." }
#
# ─────────────────────────────────────────────────────────────

HOOKS_DIR="$(cd "$(dirname "$0")" && pwd)"
CONFIG_FILE="${HOOKS_DIR}/descope-auth.config.json"
LOG_FILE="${HOOKS_DIR}/descope-auth.log"

# ─── Logging (stderr only, never stdout) ─────────────────────

log() {
  echo "[descope-auth] $(date -u +%Y-%m-%dT%H:%M:%SZ) $*" >> "$LOG_FILE" 2>&1
}

# ─── Dependency check ────────────────────────────────────────

if ! command -v jq >/dev/null 2>&1; then
  echo '{"permission": "allow"}'
  log "WARNING: jq not found, bypassing auth"
  exit 0
fi

if ! command -v curl >/dev/null 2>&1; then
  echo '{"permission": "allow"}'
  log "WARNING: curl not found, bypassing auth"
  exit 0
fi

# ─── Read hook input from Cursor ─────────────────────────────

INPUT=$(cat)
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // empty')
USER_EMAIL=$(echo "$INPUT" | jq -r '.email // empty')
CONVERSATION_ID=$(echo "$INPUT" | jq -r '.conversation_id // empty')

log "Hook fired: tool=$TOOL_NAME user=$USER_EMAIL conversation=$CONVERSATION_ID"

# ─── Load config ─────────────────────────────────────────────

if [ ! -f "$CONFIG_FILE" ]; then
  log "WARNING: Config file not found at $CONFIG_FILE, allowing without auth"
  echo '{"permission": "allow"}'
  exit 0
fi

SERVER_CONFIG=$(jq -c --arg tool "$TOOL_NAME" '
  .servers | to_entries[] |
  select(.key as $k | $tool | startswith($k)) |
  .value
' "$CONFIG_FILE" 2>/dev/null | head -1)

if [ -z "$SERVER_CONFIG" ] || [ "$SERVER_CONFIG" = "null" ]; then
  log "No auth config for tool=$TOOL_NAME, allowing without auth"
  echo '{"permission": "allow"}'
  exit 0
fi

STRATEGY=$(echo "$SERVER_CONFIG" | jq -r '.strategy')
BASE_URL=$(echo "$SERVER_CONFIG" | jq -r '.baseUrl // "https://api.descope.com"')

log "Strategy: $STRATEGY for tool=$TOOL_NAME"

# ─── Token cache (file-based, per-server) ────────────────────

CACHE_DIR="${HOOKS_DIR}/.token-cache"
mkdir -p "$CACHE_DIR"

cache_key() {
  echo "$1" | shasum -a 256 | cut -c1-16
}

get_cached_token() {
  local key=$(cache_key "$1")
  local cache_file="${CACHE_DIR}/${key}.json"

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
  local key=$(cache_key "$1")
  local cache_file="${CACHE_DIR}/${key}.json"
  echo "$2" > "$cache_file"
}

# ─── OAuth flows ─────────────────────────────────────────────

# Strategy 1: client_credentials → token exchange
do_client_credentials_exchange() {
  local client_id=$(echo "$SERVER_CONFIG" | jq -r '.clientId')
  local client_secret=$(echo "$SERVER_CONFIG" | jq -r '.clientSecret')
  local project_id=$(echo "$SERVER_CONFIG" | jq -r '.projectId')
  local audience=$(echo "$SERVER_CONFIG" | jq -r '.audience')
  local scopes=$(echo "$SERVER_CONFIG" | jq -r '.scopes // empty')
  local resource=$(echo "$SERVER_CONFIG" | jq -r '.resource // empty')

  local cache_id="cc:${client_id}:${audience}:${scopes}"
  local cached=$(get_cached_token "$cache_id") && { echo "$cached"; return 0; }

  # Step 1: client_credentials
  local cc_response=$(curl -s -X POST "${BASE_URL}/oauth2/v1/apps/token" \
    -H "Content-Type: application/json" \
    -d "$(jq -n \
      --arg grantType "client_credentials" \
      --arg clientId "$client_id" \
      --arg clientSecret "$client_secret" \
      '{grant_type: $grantType, client_id: $clientId, client_secret: $clientSecret}'
    )")

  local agent_token=$(echo "$cc_response" | jq -r '.access_token // empty')
  if [ -z "$agent_token" ]; then
    log "ERROR: client_credentials failed: $cc_response"
    return 1
  fi

  # Step 2: token exchange
  local te_body=$(jq -n \
    --arg grantType "urn:ietf:params:oauth:grant-type:token-exchange" \
    --arg clientId "$client_id" \
    --arg clientSecret "$client_secret" \
    --arg subjectToken "$agent_token" \
    --arg subjectTokenType "urn:ietf:params:oauth:token-type:access_token" \
    --arg audience "$audience" \
    --arg resource "$resource" \
    '{
      grant_type: $grantType,
      client_id: $clientId,
      client_secret: $clientSecret,
      subject_token: $subjectToken,
      subject_token_type: $subjectTokenType,
      audience: $audience
    } | if $resource != "" then . + {resource: $resource} else . end')

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

  set_cached_token "$cache_id" "$(jq -n \
    --arg token "$token" --arg expires "$expires_at" \
    '{access_token: $token, expires_at: $expires}')"

  echo "$token"
}

# Strategy 2: user token → token exchange
do_user_token_exchange() {
  local project_id=$(echo "$SERVER_CONFIG" | jq -r '.projectId')
  local user_token=$(echo "$SERVER_CONFIG" | jq -r '.userAccessToken')
  local audience=$(echo "$SERVER_CONFIG" | jq -r '.audience')
  local scopes=$(echo "$SERVER_CONFIG" | jq -r '.scopes // empty')
  local resource=$(echo "$SERVER_CONFIG" | jq -r '.resource // empty')

  local cache_id="ute:${audience}:${scopes}:${user_token: -8}"
  local cached=$(get_cached_token "$cache_id") && { echo "$cached"; return 0; }

  local te_body=$(jq -n \
    --arg grantType "urn:ietf:params:oauth:grant-type:token-exchange" \
    --arg subjectToken "$user_token" \
    --arg subjectTokenType "urn:ietf:params:oauth:token-type:access_token" \
    --arg audience "$audience" \
    --arg resource "$resource" \
    '{
      grant_type: $grantType,
      subject_token: $subjectToken,
      subject_token_type: $subjectTokenType,
      audience: $audience
    } | if $resource != "" then . + {resource: $resource} else . end')

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

  set_cached_token "$cache_id" "$(jq -n \
    --arg token "$token" --arg expires "$expires_at" \
    '{access_token: $token, expires_at: $expires}')"

  echo "$token"
}

# Strategy 3: connections API
do_connections() {
  local project_id=$(echo "$SERVER_CONFIG" | jq -r '.projectId')
  local user_token=$(echo "$SERVER_CONFIG" | jq -r '.userAccessToken')
  local app_id=$(echo "$SERVER_CONFIG" | jq -r '.appId')
  local user_id=$(echo "$SERVER_CONFIG" | jq -r '.userId')
  local tenant_id=$(echo "$SERVER_CONFIG" | jq -r '.tenantId // empty')
  local scopes=$(echo "$SERVER_CONFIG" | jq -c '.scopes // []')

  local cache_id="conn:${app_id}:${user_id}:${user_token: -8}"
  local cached=$(get_cached_token "$cache_id") && { echo "$cached"; return 0; }

  local body=$(jq -n \
    --arg appId "$app_id" \
    --arg userId "$user_id" \
    --arg tenantId "$tenant_id" \
    --argjson scopes "$scopes" \
    '{appId: $appId, userId: $userId, scopes: $scopes}
     | if $tenantId != "" then . + {tenantId: $tenantId} else . end')

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

  set_cached_token "$cache_id" "$(jq -n \
    --arg token "$token" --arg expires "$expires_at" \
    '{access_token: $token, expires_at: $expires}')"

  echo "$token"
}

# Strategy 4: CIBA
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

  # Step 1: backchannel authorize
  local auth_body=$(jq -n \
    --arg clientId "$client_id" \
    --arg clientSecret "$client_secret" \
    --arg scope "$scopes" \
    --arg audience "$audience" \
    --arg loginHint "$login_hint" \
    --arg loginHintToken "$login_hint_token" \
    --arg bindingMessage "$binding_message" \
    '{client_id: $clientId, client_secret: $clientSecret, scope: $scope, audience: $audience}
     | if $loginHint != "" then . + {login_hint: $loginHint} else . end
     | if $loginHintToken != "" then . + {login_hint_token: $loginHintToken} else . end
     | if $bindingMessage != "" then . + {binding_message: $bindingMessage} else . end')

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

  log "CIBA: waiting for user consent (auth_req_id=$auth_req_id, polling every ${poll_interval}s)"

  # Step 2: poll for token
  local elapsed=0
  while [ $elapsed -lt $timeout ]; do
    sleep "$poll_interval"
    elapsed=$((elapsed + poll_interval))

    local poll_response=$(curl -s -X POST "${BASE_URL}/oauth2/v1/apps/token" \
      -H "Content-Type: application/json" \
      -d "$(jq -n \
        --arg grantType "urn:openid:params:grant-type:ciba" \
        --arg authReqId "$auth_req_id" \
        --arg clientId "$client_id" \
        --arg clientSecret "$client_secret" \
        '{grant_type: $grantType, auth_req_id: $authReqId, client_id: $clientId, client_secret: $clientSecret}'
      )")

    local token=$(echo "$poll_response" | jq -r '.access_token // empty')
    if [ -n "$token" ]; then
      log "CIBA: user approved (${elapsed}s elapsed)"
      echo "$token"
      return 0
    fi

    local error=$(echo "$poll_response" | jq -r '.error // empty')
    case "$error" in
      authorization_pending) continue ;;
      slow_down) sleep "$poll_interval"; elapsed=$((elapsed + poll_interval)); continue ;;
      *)
        log "ERROR: CIBA poll failed: $poll_response"
        return 1
        ;;
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
    echo '{"permission": "allow"}'
    exit 0
    ;;
esac

# ─── Response to Cursor ─────────────────────────────────────

if [ -z "$TOKEN" ]; then
  log "ERROR: Failed to acquire token for tool=$TOOL_NAME"
  echo '{"permission": "deny", "reason": "Failed to acquire Descope auth token"}'
  exit 0
fi

log "SUCCESS: Token acquired for tool=$TOOL_NAME"

jq -n \
  --arg token "$TOKEN" \
  '{
    "permission": "allow",
    "headers": {
      "Authorization": ("Bearer " + $token)
    }
  }'