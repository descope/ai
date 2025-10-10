# NextJS MCP Server with Vercel MCP Adapter and Descope Node SDK

![Descope Banner](https://github.com/descope/.github/assets/32936811/d904d37e-e3fa-4331-9f10-2880bb708f64)

## Introduction

This example shows how to build an MCP server using the Vercel MCP adapter with Descope's Node SDK for session validation. The server provides a simple echo tool and demonstrates how to integrate Descope authentication with the Model Context Protocol (MCP) using Vercel's serverless functions.

## Key Components

- **Vercel MCP Adapter**: Handles the MCP protocol communication and serverless function deployment
- **Descope Node SDK**: Validates user sessions and provides authentication context
- **Echo Tool**: A simple example tool that returns a "Hello, world!" message

## Deployment

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https://github.com/descope/ai/tree/main/examples/nextjs-vercel-mcp-server&env=DESCOPE_PROJECT_ID,DESCOPE_BASE_URL&envDescription=Required%20environment%20variables%20for%20the%20MCP%20server&envLink=https://github.com/descope/ai/tree/main/examples/nextjs-vercel-mcp-server#requirements)

You can connect to the server using the [MCP Inspector](https://modelcontextprotocol.io/docs/tools/inspector) or any other MCP client. Be sure to include the `/api` path in the connection URL.

## Features

- **Session Validation**: Uses Descope Node SDK to validate JWT tokens and extract user context
- **Echo Tool**: Simple example tool demonstrating MCP integration
- **MCP Protocol**: Implements the Model Context Protocol for AI tool integration
- **Serverless Deployment**: Deploys as Vercel serverless functions for scalability
- **Type Safety**: Full TypeScript support with proper type definitions

## Requirements

Before proceeding, make sure you have the following:

- [Node.js](https://nodejs.org/) (version 18 or later)
- A valid Descope [Project ID](https://app.descope.com/settings/project)
- The Descope Inbound Apps feature enabled
- Git installed

## Running the Server

First, add the environment variables in a `.env` file at the root:

```bash
DESCOPE_PROJECT_ID=      # Your Descope project ID
DESCOPE_BASE_URL=        # Your Descope base URL (optional, defaults to https://api.descope.com)
```

Then, install dependencies:

```bash
npm i
```

Finally, run the server:

```bash
npm run dev
```

The server will start on port 3000 (or the port specified in your environment variables).

## API Endpoints

- `GET/POST /api/[transport]`: Handles incoming MCP protocol messages (supports SSE and HTTP transports)

## Authentication

The server uses Descope's Node SDK for session validation. The `verifyToken` function:

1. Extracts the bearer token from the request
2. Uses the Descope Node SDK to validate the session
3. Returns authentication context including user scopes and client ID
4. All MCP endpoints require a valid bearer token

## Managing API Keys and OAuth Tokens for Tools

If you want Descope to manage your API keys or OAuth tokens for tools, you can use functions in the Node SDK to fetch outbound app tokens at either a user or tenant level:

```typescript
// Fetch user token with specific scopes
const userToken =
  await descopeClient.management.outboundApplication.fetchTokenByScopes(
    "my-app-id",
    "user-id",
    ["read", "write"],
    { withRefreshToken: false },
    "tenant-id"
  );

// Fetch latest user token
const latestUserToken =
  await descopeClient.management.outboundApplication.fetchToken(
    "my-app-id",
    "user-id",
    "tenant-id",
    { forceRefresh: false }
  );

// Fetch tenant token with specific scopes
const tenantToken =
  await descopeClient.management.outboundApplication.fetchTenantTokenByScopes(
    "my-app-id",
    "tenant-id",
    ["read", "write"],
    { withRefreshToken: false }
  );

// Fetch latest tenant token
const latestTenantToken =
  await descopeClient.management.outboundApplication.fetchTenantToken(
    "my-app-id",
    "tenant-id",
    { forceRefresh: false }
  );
```

## Available Tools

- **echo**: Returns a simple "Hello, world!" message
