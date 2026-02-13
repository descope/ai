# 🔐 Descope Agent Hooks

**Secure your AI agent's MCP tool calls with scoped OAuth tokens — using native hook systems in Cursor and Claude Code.**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Cursor](https://img.shields.io/badge/Cursor-supported-green.svg)](#cursor)
[![Claude Code](https://img.shields.io/badge/Claude_Code-supported-green.svg)](#claude-code)

---

## The Problem

When AI agents call MCP servers, every request needs authentication. Without enforcement at the execution layer, agents operate with static tokens, overly broad credentials, or no auth at all — creating security blind spots that grow with every tool call.

## The Solution

**Agent Hooks** intercept MCP tool calls at the source — before they leave the agent — and acquire short-lived, scoped tokens from [Descope](https://descope.com). The agent never manages credentials. Auth is transparent, enforced, and automatic.

```
┌────────────┐  tool call  ┌──────────────────┐  Bearer token  ┌────────────┐
│  AI Agent  │ ───────────►│  Descope Hook    │ ──────────────►│ MCP Server │
│            │             │                  │                │            │
│ Cursor or  │             │ Acquire scoped   │                │ GitHub     │
│ Claude Code│ ◄───────────│ token from       │                │ Salesforce │
│            │  allow +    │ Descope          │                │ Google     │
│            │  auth header│                  │                │ etc.       │
└────────────┘             └──────────────────┘                └────────────┘
```

**No SDK. No runtime. Just `jq` + `curl`.**

---

## Quick Start

### Cursor

```bash
curl -fsSL https://agent-hooks.sh/install.sh | bash
```

Then edit `~/.cursor/hooks/descope-auth.config.json` with your Descope credentials and restart Cursor.

### Claude Code

```bash
curl -fsSL https://agent-hooks.sh/install-claude-code.sh | bash
```

Then edit `hooks/descope-auth.config.json` with your Descope credentials. Hooks activate on the next MCP tool call.

---

## Four Auth Strategies

Each strategy maps to a real-world deployment pattern. Pick the one that matches how your agent authenticates.

### 1. Client Credentials + Token Exchange

**The agent authenticates as itself**, then exchanges for a scoped MCP server token. Two HTTP calls, fully automated.

```
Agent ──client_credentials──► Descope /apps/token ──► agent_access_token
Agent ──token_exchange──────► Descope /apps/{pid}/token ──► scoped_mcp_token
```

```json
{
  "strategy": "client_credentials_exchange",
  "projectId": "P2xxxxxxxxx",
  "clientId": "DS_xxxxxxxx",
  "clientSecret": "ds_xxxxxxxx",
  "audience": "mcp-server-github",
  "scopes": "repo:read issues:write"
}
```

**Best for:** M2M agents, CI/CD pipelines, scheduled tasks — anything with no user session.

### 2. User Token Exchange ⭐ Recommended

**Exchange the user's Descope access token** for a narrowly-scoped MCP server token. One HTTP call. Least privilege, most secure.

```
User access_token ──token_exchange──► Descope /apps/{pid}/token ──► scoped_mcp_token
```

```json
{
  "strategy": "user_token_exchange",
  "projectId": "P2xxxxxxxxx",
  "userAccessToken": "eyJhbGciOi...",
  "audience": "mcp-server-salesforce",
  "scopes": "contacts:read deals:write"
}
```

**Best for:** Interactive agents where the user is already authenticated. The recommended default.

### 3. Connections API

**Retrieve a third-party provider token** via Descope's Outbound Apps.

```
User access_token ──► Descope /v1/mgmt/outbound/app/user/token ──► provider_token
```

```json
{
  "strategy": "connections",
  "projectId": "P2xxxxxxxxx",
  "userAccessToken": "eyJhbGciOi...",
  "appId": "google-contacts",
  "userId": "U2xxxxxxxxx",
  "scopes": ["https://www.googleapis.com/auth/contacts.readonly"]
}
```

> **⚠️ Security considerations:**
>
> Unlike token exchange, the Connections API returns the raw third-party provider token directly to the agent. Two things to be aware of:
>
> 1. **Trust boundary** — If the agent caches or leaks this token, it can be used to access the third-party service directly, outside the MCP server's control. With token exchange (strategies 1 & 2), external tokens stay server-side inside the MCP server.
> 2. **Token lifetime** — External tokens issued by providers like Google, HubSpot, etc. are **not controlled by Descope**. They may be long-lived (hours or permanent) unlike the short-lived ephemeral tokens Descope issues via its `/token` endpoint.

**Best for:** When the agent needs to call a third-party API directly, with no intermediary MCP server.

### 4. CIBA (Backchannel Authentication)

**Request user consent out-of-band** — push notification, email, etc. — and poll for approval. No active browser session needed.

```
Agent ──bc-authorize──► Descope ──► User (consent prompt)
Agent ──poll──────────► Descope ◄── User approves
Agent ◄── scoped_mcp_token
```

```json
{
  "strategy": "ciba",
  "projectId": "P2xxxxxxxxx",
  "clientId": "DS_xxxxxxxx",
  "clientSecret": "ds_xxxxxxxx",
  "audience": "mcp-server-calendar",
  "scopes": "events:read events:write",
  "loginHint": "kevin@descope.com",
  "bindingMessage": "Allow AI assistant to manage your calendar?"
}
```

**Best for:** Scheduled tasks, background agents, or when the user is on a different device.

---

## Decision Matrix

|                                      | Client Creds (1) | Token Exchange (2)     | Connections (3)      | CIBA (4)              |
| ------------------------------------ | ---------------- | ---------------------- | -------------------- | --------------------- |
| User session required                | No               | Yes                    | Yes                  | No                    |
| Token stays server-side              | ✅               | ✅                     | ❌                   | ✅                    |
| Token lifetime controlled by Descope | ✅               | ✅                     | ❌                   | ✅                    |
| User consent                         | None             | Implicit               | Implicit             | Explicit              |
| Latency                              | ~2 calls         | ~1 call                | ~1 call              | Seconds–minutes       |
| **Best for**                         | **M2M agents**   | **Interactive agents** | **Direct API calls** | **Background agents** |

---

## How It Works

### Cursor — Direct Header Injection

Cursor's `beforeMCPExecution` hook can return headers that get injected into the outbound MCP request. One script, no proxy.

```
Cursor ──stdin──► descope-auth.sh ──► {"permission":"allow","headers":{"Authorization":"Bearer ..."}}
```

**Files:**

```
~/.cursor/
├── hooks.json                     # Registers the hook
└── hooks/
    ├── descope-auth.sh            # Hook script
    └── descope-auth.config.json   # Server → strategy mapping
```

### Claude Code — Hook + MCP Wrapper

Claude Code's `PreToolUse` hooks can allow or block tool calls but **cannot inject headers**. So we use two components:

1. **PreToolUse hook** — acquires the token, writes it to a shared cache
2. **MCP wrapper** — launched as the MCP server, reads the cache, proxies with `Authorization` header

```
Claude Code ──PreToolUse──► descope-auth-cc.sh ──► writes .token-cache/server.json
Claude Code ──tool call───► descope-mcp-wrapper.sh ──reads cache──► upstream MCP + Bearer token
```

**Files:**

```
your-project/
├── .claude/
│   └── settings.json              # Hook + MCP server registration
└── hooks/
    ├── descope-auth-cc.sh         # PreToolUse hook
    ├── descope-mcp-wrapper.sh     # MCP auth wrapper
    └── descope-auth.config.json   # Server → strategy mapping
```

### Platform Comparison

|                    | Cursor                 | Claude Code                 |
| ------------------ | ---------------------- | --------------------------- |
| Hook type          | `beforeMCPExecution`   | `PreToolUse`                |
| Can inject headers | ✅                     | ❌ (needs wrapper)          |
| Tool name format   | `github_create_issue`  | `mcp__github__create_issue` |
| Files needed       | 1 script               | 2 scripts                   |
| Config location    | `~/.cursor/hooks.json` | `.claude/settings.json`     |

---

## API Endpoints

All Descope OAuth requests use **JSON bodies** (`Content-Type: application/json`).

| Operation          | Endpoint                                  |
| ------------------ | ----------------------------------------- |
| Client Credentials | `POST /oauth2/v1/apps/token`              |
| Token Exchange     | `POST /oauth2/v1/apps/{project_id}/token` |
| CIBA Authorize     | `POST /oauth2/v1/apps/bc-authorize`       |
| CIBA Poll          | `POST /oauth2/v1/apps/token`              |
| Connections        | `POST /v1/mgmt/outbound/app/user/token`   |

> The token exchange endpoint is project-scoped (`/apps/{project_id}/token`) while `client_credentials` uses the base path (`/apps/token`).

---

## Configuration

Both platforms use the same `descope-auth.config.json`:

```jsonc
{
  "servers": {
    "github": {
      "strategy": "client_credentials_exchange",
      "projectId": "P2xxxxxxxxx",
      "clientId": "DS_xxxxxxxx",
      "clientSecret": "ds_xxxxxxxx",
      "audience": "mcp-server-github",
      "scopes": "repo:read issues:write",
    },
    "salesforce": {
      "strategy": "user_token_exchange",
      "projectId": "P2xxxxxxxxx",
      "userAccessToken": "eyJhbGciOi...",
      "audience": "mcp-server-salesforce",
      "scopes": "contacts:read deals:write",
    },
  },
}
```

Keys in `servers` are matched against tool names. Cursor matches by prefix (`github` matches `github_create_issue`). Claude Code matches the server segment from `mcp__github__create_issue`.

> **⚠️ Never commit secrets.** Use environment variables, a `.env` file (git-ignored), or a secrets manager in production.

---

## Token Caching

Both hooks include a file-based token cache (`hooks/.token-cache/`) that prevents redundant Descope calls:

- Tokens are cached per-server with a **30-second expiry buffer**
- Cache files are JSON: `{"access_token": "...", "expires_at": "2025-02-12T..."}`
- Expired tokens are automatically refreshed on the next tool call
- The cache directory is created at runtime and should be git-ignored

---

## Extending

Chain multiple hooks for auth + audit, auth + policy enforcement, etc.

**Cursor:**

```json
{
  "hooks": {
    "beforeMCPExecution": [
      { "command": "./hooks/descope-auth.sh" },
      { "command": "./hooks/audit-logger.sh" }
    ]
  }
}
```

**Claude Code:**

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "^mcp__",
        "hooks": [
          { "type": "command", "command": "hooks/descope-auth-cc.sh" },
          { "type": "command", "command": "hooks/audit-logger.sh" }
        ]
      }
    ]
  }
}
```

---

## TypeScript Library

For Node.js-based agents or custom integrations, a TypeScript library is also available with the same four strategies as a programmatic API:

```typescript
import { preToolUseHook } from "@descope/agent-hooks";

const result = await preToolUseHook({
  type: "user_token_exchange",
  config: { projectId: "P2xxx" },
  userAccessToken: session.token,
  exchange: {
    audience: "mcp-server-salesforce",
    scopes: "contacts:read deals:write",
  },
});

headers["Authorization"] = `Bearer ${result.accessToken}`;
```

See [`typescript/src/descope-agent-hooks.ts`](typescript/src/descope-agent-hooks.ts) for the full API.

---

## Testing

A test agent validates the hooks without requiring live Descope credentials:

```bash
node test-agent/test-agent.mjs
```

Use `--integration` to run full tests with valid credentials. See [test-agent/README.md](test-agent/README.md) for details.

## Requirements

- `jq` — JSON processing
- `curl` — HTTP requests
- A [Descope](https://descope.com) project with OAuth apps configured

No Node.js, Python, or other runtimes required for the shell hooks (Node.js needed only for the test agent).

---

## License

MIT — see [LICENSE](LICENSE).

---

<p align="center">
  Built by <a href="https://descope.com">Descope</a> · <a href="https://agent-hooks.sh">agent-hooks.sh</a> · <a href="https://github.com/descope/agent-hooks">GitHub</a>
</p>
