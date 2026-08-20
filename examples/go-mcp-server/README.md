# Descope Go MCP Server (Sample)

A sample MCP (Model Context Protocol) server written in Go, built with the official
[modelcontextprotocol/go-sdk](https://github.com/modelcontextprotocol/go-sdk), demonstrating
an OAuth-protected MCP server secured with Descope. This is meant as a minimal, deployable
template you can clone and build on, not just a local demo.

## Overview

This server exposes a single `echo` tool over the streamable HTTP transport, and enforces
Descope session-token authentication (OAuth 2.0 Bearer tokens) on every request using the
official SDK's built-in `auth.RequireBearerToken` middleware.

## Features

- Built with the official `modelcontextprotocol/go-sdk`
- Streamable HTTP transport only, stateless (no session-ID bookkeeping)
- Descope OAuth Bearer-token validation, enforced via a single HTTP-layer middleware
- RFC 9728 OAuth Protected Resource Metadata discovery document, served unauthenticated
- Config via environment variables

## Requirements

- Go 1.26.6+
- A Descope project

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `DESCOPE_PROJECT_ID` | Yes | none | Your Descope project ID |
| `ADDR` | No | `:8080` | Address the HTTP server listens on |
| `DESCOPE_BASE_URL` | No | `https://api.descope.com` | Descope's API base URL. Change only for custom regions or domains |
| `DESCOPE_ISSUER_URL` | No | Derived from `DESCOPE_BASE_URL` and `DESCOPE_PROJECT_ID` | Override the OAuth issuer URL. Needed only for custom Descope domains |
| `SERVER_URL` | No | `http://localhost` plus the port from `ADDR` | This server's own public URL, used to build the discovery document |

Copy `.env.example` to `.env`, fill in your values, and export them into your shell.

## Running

```bash
export DESCOPE_PROJECT_ID=your_project_id
go run ./cmd/main.go
```

The server listens on `/mcp` (default `:8080`), with the discovery document served at
`/.well-known/oauth-protected-resource`.

## Descope Auth Setup

1. Create a Descope project and note its Project ID.
2. Obtain a session token for a caller. For testing, use the Client Credentials flow with a
   Descope Access Key (see "Testing with curl" below).
3. Send the token as `Authorization: Bearer <token>` on every request to `/mcp`.
4. Requests without a valid token receive a `401 Unauthorized` response with a
   `WWW-Authenticate` header pointing callers to the discovery document.

## Testing with curl

```bash
# 1. Get a token via Client Credentials, using a Descope Access Key
curl -X POST https://api.descope.com/oauth2/v1/token \
  -H "Authorization: Basic $(echo -n '<ProjectID>:<AccessKey>' | base64)" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials&scope=openid profile email"

# 2. Initialize, with the token
curl -i -X POST http://localhost:8080/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "Authorization: Bearer <token>" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"curl-test","version":"1.0"}}}'

# 3. Call the echo tool
curl -X POST http://localhost:8080/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "Authorization: Bearer <token>" \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"echo","arguments":{"message":"hello"}}}'
```

## Available Tools

- **echo**: takes a `message` string and returns it back as is. A minimal template tool;
  replace it with your own logic.

## Deploying

This is a plain Go HTTP server, so it builds and runs as a standard container image on any
platform that accepts one.

```bash
docker build -t go-mcp-server .
docker run -p 8080:8080 -e DESCOPE_PROJECT_ID=your_project_id go-mcp-server
```

From there, deploy the image with whichever platform you prefer, for example:
- Google Cloud Run: `gcloud run deploy --source .`
- Fly.io: `fly launch`
- Any container host that accepts a standard Docker image

## Beyond This Sample: Other Descope Go SDK Capabilities

This sample only demonstrates session-token validation. The same
[Descope Go SDK](https://github.com/descope/go-sdk) also supports, if your own MCP server's
tools need them:

- **Token exchange**: exchanging one token type for another
- **Connections token fetching**: retrieving a user's already-authorized tokens for other
  connected services, so your tools can call third-party APIs on the user's behalf
- **Management functions**: broader administrative operations, including user, role, and
  tenant management

See the [Descope Go SDK documentation](https://github.com/descope/go-sdk) for details.
