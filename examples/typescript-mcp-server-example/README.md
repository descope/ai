# Vanilla TypeScript MCP Server with Descope Auth

This example is a remote MCP server built with TypeScript + Express and protected with Descope.

It exposes:

- MCP endpoint: `/mcp`
- OAuth protected resource metadata: `/.well-known/oauth-protected-resource`

## Prerequisites

- Node.js 20+ (or newer)
- A Descope Project
- An "MCP Server" configured in Descope

You must create the [MCP server](https://docs.descope.com/agentic-identity-hub/mcp-servers) in Descope first, so you can get the authorization server issuer URL used to protect this server.

## 1) Create the Descope MCP Server

In Descope Console:

1. Create or open your project.
2. Create an [MCP server](https://app.descope.com/agentic-hub/mcp-servers) in Descope for this MCP Server.
3. Copy the MCP server issuer URL, for example:
   `https://api.descope.com/v1/apps/agentic/...`

## 2) Configure Environment Variables

Copy `.env.example` to `.env` and fill in values:

```bash
cp .env.example .env
```

Required values:

- `PORT` - local port to run the server (example: `3002`)
- `SERVER_URL` - public/base URL for this server (must match port, example: `http://localhost:3002`)
- `DESCOPE_PROJECT_ID` - your Descope project ID
- `DESCOPE_MCP_SERVER_ISSUER` - issuer URL from your Descope MCP server config

Optional:

- `DESCOPE_BASE_URL` (defaults to `https://api.descope.com`)

## 3) Install and Run

```bash
npm install
npm start
```

For watch mode:

```bash
npm run dev
```

## 4) Validate Well-Known Metadata

```bash
curl http://localhost:3002/.well-known/oauth-protected-resource
```

Expected shape:

```json
{
  "resource": "http://localhost:3002/mcp",
  "authorization_servers": ["https://api.descope.com/v1/apps/<...>"]
}
```

## 5) Connect as a Remote MCP Server

Use this MCP URL in your client:

- `http://localhost:<PORT>/mcp`

During OAuth discovery, the client reads:

- `http://localhost:<PORT>/.well-known/oauth-protected-resource`

and then uses your Descope authorization server for token issuance/validation.

## Project Structure

- `src/index.ts` - Express app, auth middleware wiring, and MCP transport
- `src/create-server.ts` - MCP server/tool registration
- `.env.example` - required env variable template

## Troubleshooting

- If metadata shows the wrong `authorization_servers`, verify route order in `src/index.ts` and restart the server.
- If `npm start` fails with missing `build/index.js`, run `npm run build` first (or keep the current `start` script that builds automatically).
- Ensure `SERVER_URL` and `PORT` match (for example both `3002`).
