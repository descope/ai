# Auth Strategies — Deep Dive

For the full guide, see the [README](../README.md). This document covers
implementation details and edge cases for each strategy.

## Descope API Endpoints

All requests use JSON bodies (`Content-Type: application/json`).

| Operation          | Endpoint                                  |
| ------------------ | ----------------------------------------- |
| Client Credentials | `POST /oauth2/v1/apps/token`              |
| Token Exchange     | `POST /oauth2/v1/apps/{project_id}/token` |
| CIBA Authorize     | `POST /oauth2/v1/apps/bc-authorize`       |
| CIBA Poll          | `POST /oauth2/v1/apps/token`              |
| Connections        | `POST /v1/mgmt/outbound/app/user/token`   |

The token exchange endpoint is project-scoped (`/apps/{project_id}/token`)
while `client_credentials` uses the base path (`/apps/token`).

## Strategy 1: Client Credentials + Token Exchange

**Grant types used:**

1. `client_credentials` — agent authenticates as itself
2. `urn:ietf:params:oauth:grant-type:token-exchange` — narrow to MCP server scope

**Step 1 — Client Credentials:**

```bash
curl -X POST 'https://api.descope.com/oauth2/v1/apps/token' \
  -H 'Content-Type: application/json' \
  -d '{
    "grant_type": "client_credentials",
    "client_id": "",
    "client_secret": ""
  }'
```

**Step 2 — Token Exchange:**

```bash
curl -X POST 'https://api.descope.com/oauth2/v1/apps/{project_id}/token' \
  -H 'Content-Type: application/json' \
  -d '{
    "grant_type": "urn:ietf:params:oauth:grant-type:token-exchange",
    "client_id": "",
    "client_secret": "",
    "subject_token": "",
    "subject_token_type": "urn:ietf:params:oauth:token-type:access_token",
    "audience": "",
    "resource": ""
  }'
```

## Strategy 2: User Token Exchange

**Grant type:** `urn:ietf:params:oauth:grant-type:token-exchange`

Same as Step 2 above, but `subject_token` is the user's Descope access token
instead of a client_credentials token.

```bash
curl -X POST 'https://api.descope.com/oauth2/v1/apps/{project_id}/token' \
  -H 'Content-Type: application/json' \
  -d '{
    "grant_type": "urn:ietf:params:oauth:grant-type:token-exchange",
    "subject_token": "",
    "subject_token_type": "urn:ietf:params:oauth:token-type:access_token",
    "audience": ""
  }'
```

## Strategy 3: Connections API

**Endpoint:** `POST /v1/mgmt/outbound/app/user/token`

**Auth header:** `Bearer <project_id>:<access_token>`

```bash
curl -X POST 'https://api.descope.com/v1/mgmt/outbound/app/user/token' \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer :' \
  -d '{
    "appId": "google-contacts",
    "userId": "xxxxx",
    "tenantId": "optional-tenant-id",
    "scopes": [
      "https://www.googleapis.com/auth/contacts.readonly"
    ],
    "options": {
      "withRefreshToken": false,
      "forceRefresh": false
    }
  }'
```

### Security Considerations

- The raw third-party provider token is returned directly to the agent
- External tokens (Google, HubSpot, etc.) are NOT controlled by Descope
  and may be long-lived (hours or permanent)
- With token exchange (strategies 1 & 2), external tokens stay server-side
  inside the MCP server and the agent only holds short-lived Descope tokens

## Strategy 4: CIBA

**Grant type:** `urn:openid:params:grant-type:ciba`

**Step 1 — Backchannel Authorize:**

```bash
curl -X POST 'https://api.descope.com/oauth2/v1/apps/bc-authorize' \
  -H 'Content-Type: application/json' \
  -d '{
    "client_id": "",
    "client_secret": "",
    "scope": "events:read events:write",
    "audience": "mcp-server-calendar",
    "login_hint": "user@example.com",
    "binding_message": "Allow AI assistant to manage your calendar?"
  }'
```

Returns `auth_req_id` and optional `interval`.

**Step 2 — Poll for Token:**

```bash
curl -X POST 'https://api.descope.com/oauth2/v1/apps/token' \
  -H 'Content-Type: application/json' \
  -d '{
    "grant_type": "urn:openid:params:grant-type:ciba",
    "auth_req_id": "",
    "client_id": "",
    "client_secret": ""
  }'
```

**Poll responses:**

- `authorization_pending` — keep polling
- `slow_down` — increase poll interval, keep polling
- `expired_token` — request expired, start over
- `access_denied` — user rejected
- Success — returns `access_token`
