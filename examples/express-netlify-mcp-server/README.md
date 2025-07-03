# Express MCP Server with Streamable HTTP Transport and Descope MCP Auth SDK

![Descope Banner](https://github.com/descope/.github/assets/32936811/d904d37e-e3fa-4331-9f10-2880bb708f64)

## Introduction

This example shows how to add auth to a Streamable HTTP MCP Server using Descope's MCP Auth SDK (Express) and deploy it to Netlify. It handles fetching weather-related data.

## Requirements

Before proceeding, make sure you have the following:

- A valid Descope [Project ID](https://app.descope.com/settings/project) and [Management Key](https://app.descope.com/settings/company/managementkeys)
- [Dynamic Client Registration](https://docs.descope.com/identity-federation/inbound-apps/creating-inbound-apps#method-2-dynamic-client-registration-dcr) enabled on Inbound Apps in Descope

## Speedily Deploy the Server

Deploy your own version of this example site, by clicking the Deploy to Netlify Button below. This will automatically:

- Clone a copy of this example from the examples repo to your own GitHub account
- Create a new project in your [Netlify account](https://app.netlify.com/?utm_medium=social&utm_source=github&utm_campaign=devex-ph&utm_content=devex-examples), linked to your new repo, with required environment variables
- Create an automated deployment pipeline to watch for changes on your repo
- Build and deploy your new site
- This repo can then be used to iterate on locally using `netlify dev`

[![Deploy to Netlify](https://www.netlify.com/img/deploy/button.svg)](https://app.netlify.com/start/deploy?repository=https://github.com/descope/ai&create_from_path=examples/express-netlify-mcp-server)

You can connect to the server using the [Cloudflare Playground](https://playground.ai.cloudflare.com/), [MCP Inspector](https://modelcontextprotocol.io/docs/tools/inspector) or any other MCP client. Be sure to include the `/mcp` path in the connection URL.

## Install and run the examples locally

You can clone this entire examples repo to explore this and other examples, and to run them locally.

```shell

# 1. Clone the examples repository to your local development environment
git clone https://github.com/descope/ai.git

# 2. Move into the project directory for this example
cd examples/express-netlify-mcp-server

#3. Add the environment variables in a `.env` file

DESCOPE_PROJECT_ID=      # Your Descope project ID
DESCOPE_MANAGEMENT_KEY=  # Your Descope management key
SERVER_URL=             # The URL where your server is hosted
DESCOPE_BASE_URL=       # Your Descope Base URL

# 3. Install the Netlify CLI to let you locally serve your site using Netlify's features
npm i -g netlify-cli

# 4. Serve your site using Netlify Dev to get local serverless functions
netlify dev

# 5. While the site is running locally, open a separate terminal tab to run the MCP inspector or client you desire
npx @modelcontextprotocol/inspector npx mcp-remote@next http://localhost:8888/mcp

```

## Features

- Real-time weather data streaming
- Secure authentication using Descope
- MCP Authorization Compliant

## API Endpoints

- `POST /mcp`: Handles incoming messages for the MCP protocol

## Authentication

The server uses Descope for authentication. All MCP endpoints except the authentication router require a valid bearer token.

## Netlify Configuration

Importantly, because of how Express handles mapping routes, ensure you set the `netlify.toml` redirects to the correct path.

```toml
[[redirects]]
  from = "/mcp"
  to = "/.netlify/functions/express-mcp-server"
  status = 200
  force = true

[[redirects]]
  from = "/.well-known/oauth-authorization-server"
  to = "/.netlify/functions/express-mcp-server"
  status = 200
  force = true

[[redirects]]
  from = "/.well-known/oauth-protected-resource"
  to = "/.netlify/functions/express-mcp-server"
  status = 200
  force = true
```


