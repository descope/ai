# Descope Go MCP Server (Sample)

A sample MCP (Model Context Protocol) server built with [mcp-go](https://github.com/mark3labs/mcp-go), demonstrating Descope session-token authentication over the streamable HTTP transport.

## Overview

This server exposes a single demo tool, `hello_world`, and enforces Descope authentication on every request when running over HTTP. Local stdio mode is available for quick development without auth.

## Features

- Built with `mark3labs/mcp-go`
- Supports both `stdio` and streamable HTTP transports
- Descope JWT session validation, enforced at two layers when running over HTTP (Resource Server pattern):
  1. **HTTP-level gate** (primary): an `http.Handler` middleware validates the bearer token before the request reaches the MCP layer, returning a real `401 Unauthorized` with a `WWW-Authenticate` header per the [MCP Authorization spec](https://modelcontextprotocol.io/specification/2025-06-18/basic/authorization) and [RFC 9728](https://datatracker.ietf.org/doc/html/rfc9728). The OAuth 2.0 Protected Resource Metadata document is served at `/.well-known/oauth-protected-resource` (unauthenticated, as required for discovery).
  2. **Tool-call middleware** (defense in depth): re-validates the token before the `hello_world` handler runs.

  In `stdio` mode neither layer is registered, so tool calls are never authenticated — stdio is local-dev only.
- Config via environment variables

## Requirements

- Go 1.2x+
- A Descope project (Project ID)

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `DESCOPE_PROJECT_ID` | Yes | — | Your Descope project ID |
| `ADDR` | No | `:8080` | Address the HTTP server listens on |
| `SERVER_URL` | No | `http://localhost<ADDR>` | This server's externally-reachable base URL, advertised as the OAuth Protected Resource identifier (RFC 9728). Set this to your real public URL in any non-local deployment. |
| `DESCOPE_BASE_URL` | No | `https://api.descope.com` | Advertised to clients as the authorization server in the protected resource metadata document. Does not change how this server talks to Descope's API. |

Copy `.env.example` to `.env` and fill in your values, then export them into your shell (or use a tool like `direnv`).

## Running

### stdio (local dev, no auth enforced)
```bash
go run ./cmd/main.go --transport stdio
```

### HTTP (auth enforced)
```bash
export DESCOPE_PROJECT_ID=your_project_id
go run ./cmd/main.go --transport http
```

The server listens on `/mcp` (default `:8080`).

## Descope Auth Setup

1. Create a Descope project and note its Project ID.
2. Obtain a session token for a caller (e.g. via an Access Key + Client Credentials flow, or a full user login).
3. Send it as `Authorization: Bearer <token>` on every request to `/mcp`.
4. Requests without a valid token receive an HTTP `401 Unauthorized` with a `WWW-Authenticate: Bearer resource_metadata="<discovery-url>"` header — clients can fetch that URL for the Protected Resource Metadata document instead of guessing how to authenticate.

## Testing with curl

```bash
# 0. No token -> 401 + WWW-Authenticate (no Mcp-Session-Id is ever issued)
curl -i -X POST http://localhost:8080/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"curl-test","version":"1.0"}}}'

# 1. Initialize with a valid bearer token (get a session ID)
curl -i -X POST http://localhost:8080/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "Authorization: Bearer <your-token>" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"curl-test","version":"1.0"}}}'

# 2. Call the tool (with the session ID and a valid bearer token)
curl -X POST http://localhost:8080/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "Mcp-Session-Id: <session-id-from-step-1>" \
  -H "Authorization: Bearer <your-token>" \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"hello_world","arguments":{"name":"World"}}}'

# 3. Discovery document (no auth required)
curl -i http://localhost:8080/.well-known/oauth-protected-resource
```
