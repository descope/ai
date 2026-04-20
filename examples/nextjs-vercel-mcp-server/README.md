# Next.js MCP Server with Vercel MCP Handler and Descope Node SDK

![Descope Banner](https://github.com/descope/.github/assets/32936811/d904d37e-e3fa-4331-9f10-2880bb708f64)

## Introduction

This example shows how to build an MCP server using the Vercel [MCP Handler](https://github.com/vercel/mcp-handler) with Descope's Node SDK for session validation. The server provides a simple echo tool and demonstrates how to integrate Descope authentication with the Model Context Protocol (MCP) using Vercel's serverless functions.

## Key Components

- **Vercel's [mcp-handler](https://github.com/vercel/mcp-handler)**: Handles the MCP protocol communication and serverless function deployment
- **Descope Node SDK**: Validates user sessions and provides authentication context
- **Echo Tool**: A simple example tool that returns a "Hello, world!" message

## Deployment

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https%3A%2F%2Fgithub.com%2Fdescope%2Fai%2Ftree%2Fmain%2Fexamples%2Fnextjs-vercel-mcp-server&env=NEXT_PUBLIC_DESCOPE_PROJECT_ID&envDescription=Your%20Descope%20Project%20ID&envLink=https%3A%2F%2Fapp.descope.com%2Fsettings%2Fproject)

You can connect to the server using the [MCP Inspector](https://modelcontextprotocol.io/docs/tools/inspector) or any other MCP client. Be sure to include the `/api/mcp` path in the connection URL.

## Requirements

Before proceeding, make sure you have the following:

- [Node.js](https://nodejs.org/) (version 20 or later)
- A valid Descope [Project ID](https://app.descope.com/settings/project)
- An MCP server registered in Descope (see below) so you have an **Issuer URL** for this deployment

## Running the Server

In the [Descope Console](https://app.descope.com/agentic-hub/mcp-servers), you will need to create an [MCP server](https://docs.descope.com/agentic-identity-hub/mcp-servers).

Once completed, copy that MCP server’s **Issuer URL**—you will set it as `DESCOPE_MCP_ISSUER_URL`. Without it, clients cannot discover or use the hosted auth flows against your server.

Then add the environment variables in a `.env` file at the root:

```bash
# Your Descope project ID
NEXT_PUBLIC_DESCOPE_PROJECT_ID=
# Issuer URL from your MCP server in Descope (MCP server configuration)
DESCOPE_MCP_ISSUER_URL=

# Your Descope base URL (optional)
NEXT_PUBLIC_DESCOPE_BASE_URL=
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

## Available Tools

- **echo**: Returns a simple "Hello, world!" message
