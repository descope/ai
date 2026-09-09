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
| `DESCOPE_ISSUER_URL` | Yes | none | This project's OAuth issuer URL, e.g. `https://api.descope.com/v1/apps/<ProjectID>` |
| `ADDR` | No | `:8080` | Address the HTTP server listens on |
| `SERVER_URL` | No | `http://localhost` plus the port from `ADDR` | This server's own public URL, used to build the discovery document |

Copy `.env.example` to `.env`, fill in your values, and export them into your shell.

## Running

```bash
export DESCOPE_PROJECT_ID=your_project_id
export DESCOPE_ISSUER_URL=https://api.descope.com/v1/apps/your_project_id
go run ./cmd/main.go
```

The server listens on `/mcp` (default `:8080`), with the discovery document served at
`/.well-known/oauth-protected-resource`.

## Descope Auth Setup

This server's session validation (`ValidateSessionWithToken`) accepts both of the issuer
shapes below unchanged — the only difference between the two setups is what you put in
`DESCOPE_ISSUER_URL` and whether you configure anything extra in the Console.

### Quick Start (Simple Pattern)

This is the default/recommended path for local dev. It validates plain Descope session tokens
directly — there's no Inbound App, no Dynamic Client Registration, and no separate Console
resource to create. Any valid Descope session token works, however the caller obtained it.

1. Create a Descope project and note its Project ID. Nothing else needs to be set up in the
   Console for this sample.
2. Set `DESCOPE_ISSUER_URL` from the Project ID alone:
   `https://api.descope.com/v1/apps/<ProjectID>`.
3. Obtain a session token for a caller. For testing, use the Client Credentials flow with a
   Descope Access Key (see "Testing with curl" below).
4. Send the token as `Authorization: Bearer <token>` on every request to `/mcp`.
5. Requests without a valid token receive a `401 Unauthorized` response with a
   `WWW-Authenticate` header pointing callers to the discovery document. The `echo` tool
   additionally requires an `mcp:echo` scope on the token — see "Available Tools" below.

### Production Setup with User-Delegated Auth (MCP Server Resource Pattern)

For production use, or to support interactive MCP clients (Claude, Cursor, VS Code, MCP
Inspector) doing a real browser-based OAuth login and per-tool scope consent, register this
server as an **MCP Server Resource** in the Descope Console instead:

1. Go to **Agentic Identity Hub → MCP Servers**
   (`https://app.descope.com/agentic-hub/mcp-servers`) in the Descope Console.
2. Click **+ MCP Server**, give it a name, and set **MCP Server URL** to your server's real
   URL (e.g. `http://localhost:8080` for local testing).
3. Under **MCP Server Scopes**, add a scope — e.g. `mcp:echo` — with a description shown on
   the consent screen (e.g. "Access to the echo tool").
4. Under **MCP Client Registration**, enable **CIMD** and/or **DCR** if you want interactive
   MCP clients (Claude, Cursor, MCP Inspector) to register automatically.
5. Click **Create**. On the confirmation page, expand **Usage Samples** and copy the **Issuer
   URL** (format: `https://api.descope.com/v1/apps/agentic/<ProjectID>/<AppID>`).
6. Set `DESCOPE_ISSUER_URL` to this value instead of the simple pattern's URL.

Our Go code's session validation (`internal/auth/middleware.go`) already works correctly with
tokens from this pattern with **no code changes required** — `internal/config` accepts both
issuer shapes automatically, so only the `DESCOPE_ISSUER_URL` config value differs between the
two patterns.

## Testing with curl

### Testing the Quick Start (Simple Pattern)

```bash
# 1. Get a token via Client Credentials, using a Descope Access Key
curl -X POST https://api.descope.com/oauth2/v1/token \
  -H "Authorization: Basic $(echo -n '<ProjectID>:<AccessKey>' | base64)" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials&scope=mcp:echo"

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

Note the `scope=mcp:echo` on the token request in step 1 — the `echo` tool now requires this
scope (see "Available Tools" below); a token without it will get an
`insufficient scope: mcp:echo required` tool-level error in step 3.

#### Alternative: MCP Inspector

For a more interactive way to explore the server — schema-driven forms for tool arguments,
and the raw JSON-RPC/HTTP traffic visible as you go — you can use
[MCP Inspector](https://modelcontextprotocol.io/docs/tools/inspector) instead of curl:

```bash
npx @modelcontextprotocol/inspector
```

Connect with:
- **Transport Type**: `Streamable HTTP`
- **URL**: `http://localhost:8080/mcp`
- **Headers**: `Authorization: Bearer <token>` — the same token from step 1 above

Note that this is the same manual-token approach as the curl steps above, just with an
interactive UI — it does not demonstrate a full user-delegated OAuth login flow, since this
sample's simple session-validation pattern doesn't support that.

### Testing the MCP Server Resource Pattern

This pattern has two distinct testing paths, depending on what you're simulating:

**Machine-to-machine (no user involved):**

1. In the Console, go to **Agentic Identity Hub → Clients → + Client**, name it, and enable
   **only** the **Client Credentials** grant type.
2. Copy the generated **Client ID** and **Client Secret** directly from the creation screen.
3. Go to **Agentic Identity Hub → Policies** and create a policy with this client as the
   **subject**, your MCP Server Resource as the **target**, the specific scope(s) you want to
   grant (e.g. `mcp:echo`), and grant type **Machine-to-Machine (M2M) access**.
4. Request a token from the resource's token endpoint (from the Usage Samples section):

   ```bash
   curl -X POST https://api.descope.com/oauth2/v1/apps/agentic/<ProjectID>/<AppID>/token \
     -H "Authorization: Basic $(echo -n '<ClientID>:<ClientSecret>' | base64)" \
     -H "Content-Type: application/x-www-form-urlencoded" \
     -d "grant_type=client_credentials"
   ```

   Then use the returned token the same way as steps 2–3 above.

   Worth calling out honestly: manually-created clients need this explicit policy step to
   reach the resource at all — unlike clients registered via DCR/CIMD, which get automatic
   access to the MCP server they registered with, no policy required.

   **Known rough edge, unresolved as of this writing:** we hit a case where a manually-created
   Client + Policy combination that looked correctly configured in the Console still returned
   `{"errorCode":"E063316","errorMessage":"Application is not associated with this MCP
   server"}` on every token request. If you hit the same error, double-check your Console setup
   very carefully (grant type toggle actually saved, policy subject/target exactly matching,
   policy actually active) — or fall back to the DCR/MCP Inspector path below, which doesn't
   depend on manual policy wiring.

**Interactive / user-delegated (simulating a real MCP client):**

Use MCP Inspector, which handles the full browser-based OAuth login flow — including DCR client
registration — automatically against this pattern's resource:

```bash
npx @modelcontextprotocol/inspector
```

Connect with:
- **Transport Type**: `Streamable HTTP`
- **URL**: your server's `/mcp` URL (e.g. `http://localhost:8080/mcp`)

Leave the Authorization header unset — Inspector will detect the `401` + discovery metadata,
register itself as an OAuth client automatically (via DCR, if enabled on the resource), and walk
you through the browser login and consent screen before calling any tool.

## Available Tools

- **echo**: takes a `message` string and returns it back as is. Requires the `mcp:echo` scope
  on the caller's token — a token without it gets an `insufficient scope: mcp:echo required`
  tool-level error. A minimal template tool; replace it with your own logic.

## Deploying

This is a plain Go HTTP server, so it builds and runs as a standard container image on any
platform that accepts one.

```bash
docker build -t go-mcp-server .
docker run -p 8080:8080 \
  -e DESCOPE_PROJECT_ID=your_project_id \
  -e DESCOPE_ISSUER_URL=https://api.descope.com/v1/apps/your_project_id \
  go-mcp-server
```

From there, deploy the image with whichever platform you prefer, for example:
- Google Cloud Run: `gcloud run deploy --source .`
- Fly.io: `fly launch`
- Any container host that accepts a standard Docker image

## Beyond This Sample: Other Descope Go SDK Capabilities

This sample only demonstrates session-token validation. The same
[Descope Go SDK](https://github.com/descope/go-sdk) also supports, if your own MCP server's
tools need them:

- **Management functions**: broader administrative operations, including user, role, and
  tenant management

### Calling third-party APIs on a user's behalf (Connections / Outbound Apps)

If a tool needs to call another service — Google Calendar, Slack, GitHub, etc. — on behalf of
the authenticated user, Descope can hand back that user's already-authorized token for it. In
the Descope Console this is called a **Connection** (the same underlying concept is also called
an **Outbound App**); see
[Connections](https://docs.descope.com/agentic-identity-hub/core-components/connections) for how
to set one up.

This requires a **Management Key**, not just a Project ID — set it on the Descope client:

```go
descopeClient, err := client.NewWithConfig(&client.Config{
	ProjectID:     cfg.DescopeProjectID,
	ManagementKey: os.Getenv("DESCOPE_MANAGEMENT_KEY"),
})
if err != nil {
	log.Fatalf("failed to init descope client: %v", err)
}
```

Then, inside a tool handler, fetch the user's token for the connected service:

```go
token, err := descopeClient.Management.OutboundApplication().FetchUserToken(ctx, &descope.FetchOutboundAppUserTokenRequest{
	AppID:  "google-calendar",  // the Connection/Outbound App ID, configured in the Console
	UserID: userID,             // the authenticated user's ID, e.g. from the validated session
	Scopes: []string{"https://www.googleapis.com/auth/calendar.readonly"},
})
if err != nil {
	return nil, fmt.Errorf("fetching outbound token: %w", err)
}
// token.AccessToken can now be used to call Google's API on the user's behalf
```

See the [Descope Go SDK documentation](https://github.com/descope/go-sdk) for details.
