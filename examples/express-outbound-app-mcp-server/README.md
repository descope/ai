# Express MCP Server with Stateless Streamable HTTP Transport and Descope MCP Auth SDK

![Descope Banner](https://github.com/descope/.github/assets/32936811/d904d37e-e3fa-4331-9f10-2880bb708f64)

## Introduction

This example shows how to add auth to a Streamable HTTP MCP Server using Descope's MCP Auth SDK (Express) and deploy it to Vercel. It handles fetching weather-related data.

## Deployment

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https://github.com/descope/ai/tree/main/examples/express-mcp-server&env=DESCOPE_PROJECT_ID,DESCOPE_MANAGEMENT_KEY,SERVER_URL&envDescription=Required%20environment%20variables%20for%20the%20MCP%20server&envLink=https://github.com/descope/ai/tree/main/examples/express-mcp-server#requirements)

You can connect to the server using the [Cloudflare Playground](https://playground.ai.cloudflare.com/), [MCP Inspector](https://modelcontextprotocol.io/docs/tools/inspector) or any other MCP client. Be sure to include the `/mcp` path in the connection URL.

## Features

- Real-time weather data streaming
- Secure authentication using Descope
- MCP Authorization Compliant

## Requirements

Before proceeding, make sure you have the following:

- [Node.js](https://nodejs.org/) (version 18 or later)
- A valid Descope [Project ID](https://app.descope.com/settings/project) and [Management Key](https://app.descope.com/settings/company/managementkeys)
- The Descope Inbound Apps feature enabled
- Git installed

## Running the Server

First, add the environment variables in a `.env` file at the root:

```bash
DESCOPE_PROJECT_ID=      # Your Descope project ID
DESCOPE_MANAGEMENT_KEY=  # Your Descope management key
SERVER_URL=             # The URL where your server is hosted
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

- `GET /mcp`: Handles incoming messages for the MCP protocol

## Authentication

The server uses Descope for authentication. All MCP endpoints except the authentication router require a valid bearer token.
