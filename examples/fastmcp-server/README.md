# FastMCP Weather Server Example (Python)

![Descope Banner](https://github.com/descope/.github/assets/32936811/d904d37e-e3fa-4331-9f10-2880bb708f64)

## Introduction

This example demonstrates how to implement OAuth authentication with an external provider (Descope) using [FastMCP](https://github.com/fastmcp/fastmcp) for Model Context Protocol (MCP) tools.

The server uses FastMCP's RemoteAuthProvider (introduced in 2.11.0) to handle OAuth discovery endpoints and token validation. This enables seamless integration with Descope's Dynamic Client Registration (DCR) capabilities, allowing MCP clients to automatically register and authenticate without manual configuration.

## Requirements

- Python 3.10+
- FastMCP 2.11.0+
- [Descope Project ID](https://app.descope.com/settings/project)
- [Dynamic Client Registration](https://docs.descope.com/identity-federation/inbound-apps/creating-inbound-apps#method-2-dynamic-client-registration-dcr) enabled on Inbound Apps in Descope

## Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/descope/ai.git
cd examples/fastmcp-server
```

### 2. Set up environment variables

Create a `.env` file with:

```env
DESCOPE_PROJECT_ID=your_project_id
DESCOPE_BASE_URL=https://api.descope.com
SERVER_URL=<Your Server URL> # defaults to http://localhost:3000
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the server

```bash
python server.py
```

### 5. Open the landing page

Visit your server url or [http://localhost:3000](http://localhost:3000) for documentation and quick start info.

## Features

- Real-time weather data and alerts from the National Weather Service API
- Secure OAuth 2.0 authentication using Descope
- MCP-compliant tool endpoints
- Modern, self-documenting landing page

## API Endpoints

- `GET /` — Landing page and documentation
- `GET /mcp-server/mcp/` — Main MCP endpoint (requires Bearer token)
- `GET /.well-known/oauth-authorization-server` — OAuth 2.0 server metadata
- `GET /.well-known/oauth-protected-resource` — Resource metadata

## Authentication

The server uses Descope for authentication. All MCP endpoints require a valid Bearer token.  
Tokens are validated using FastMCP's built-in `RemoteAuthProvider` with JWT verification. This enables full OAuth 2.1 support including dynamic client registration.

The authentication flow:
1. The server validates tokens using Descope's JWKS endpoint
2. The server exposes OAuth discovery endpoints for client configuration
3. Clients can dynamically register and obtain tokens from Descope
4. The server validates tokens and their audience claims

## Adding Tools

Just use the `@mcp.tool` decorator:

```python
@mcp.tool
def get_alerts(state: str) -> str:
    ...
```

FastMCP will automatically expose this as an MCP tool!

## OAuth Discovery

FastMCP's RemoteAuthProvider automatically sets up the required OAuth discovery endpoints:

- `/.well-known/oauth-authorization-server` - Provides OAuth server metadata
- `/.well-known/oauth-protected-resource` - Describes this server as a protected resource

These endpoints enable MCP clients to automatically discover and authenticate with the Descope identity provider.

## Troubleshooting

- If you encounter authentication issues, try clearing the authentication files:
  ```bash
  rm -rf ~/.mcp-auth
  ```
- For OAuth-related issues, check that your `DESCOPE_PROJECT_ID` environment variable is set correctly.
