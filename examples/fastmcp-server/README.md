# FastMCP Weather Server Example (Python)

![Descope Banner](https://github.com/descope/.github/assets/32936811/d904d37e-e3fa-4331-9f10-2880bb708f64)

## Introduction

This example demonstrates how to implement OAuth authentication with an external provider (Descope) using [FastAPI](https://fastapi.tiangolo.com/) and [FastMCP](https://github.com/fastmcp/fastmcp) for Model Context Protocol (MCP) tools.

Here, FastMCP tools are mounted in a FastAPI server, rather than converting FastAPI APIs to MCP tools.

**New Feature**: This server now includes Descope Outbound App management tools using the latest Python SDK features from the [outbound-apps branch](https://github.com/descope/python-sdk/pull/621).

## Requirements

- Python 3.10+
- [Descope Project ID](https://app.descope.com/settings/project)
- [Dynamic Client Registration](https://docs.descope.com/identity-federation/inbound-apps/creating-inbound-apps#method-2-dynamic-client-registration-dcr) enabled on Inbound Apps in Descope
- [Descope Management Key](https://docs.descope.com/management/management-keys) (for outbound app management features)

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
DESCOPE_MANAGEMENT_KEY=your_management_key  # Optional: for outbound app management
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

Visit [http://localhost:3000](http://localhost:3000) for documentation and quick start info.

## Features

- Real-time weather data and alerts from the National Weather Service API
- Secure OAuth 2.0 authentication using Descope
- **Descope Outbound App Management** (new!)
  - List outbound applications
  - Get outbound application details
  - Create new outbound applications
  - Get outbound tokens
  - Get user tokens
  - Get tenant tokens
- MCP-compliant tool endpoints
- Modern, self-documenting landing page

## Available Tools

### Weather Tools

- `get_alerts(state: str)` - Get weather alerts for a state
- `get_forecast(latitude: float, longitude: float)` - Get weather forecast for coordinates

### Token and User Information Tools

- `get_token_info()` - Get information about the current access token structure
- `get_user_info()` - Get current user information from the access token
- `validate_token_with_descope()` - Validate the token with Descope's userinfo endpoint
- `call_descope_api_with_token(api_endpoint)` - Make custom API calls to Descope using the token
- `exchange_token_for_descope_user()` - Demonstrate token exchange with Descope SDK

### Descope Outbound App Tools

- `list_outbound_apps()` - List all outbound applications
- `get_outbound_app(app_id: str)` - Get details of a specific outbound application
- `create_outbound_app(name: str, description: str)` - Create a new outbound application
- `get_outbound_token(app_id: str)` - Get an outbound token for an application
- `get_user_token(user_id: str)` - Get a user token for a specific user
- `get_tenant_token(tenant_id: str)` - Get a tenant token for a specific tenant

## API Endpoints

- `GET /` — Landing page and documentation
- `GET /mcp-server/mcp/` — Main MCP endpoint (requires Bearer token)
- `GET /.well-known/oauth-authorization-server` — OAuth 2.0 server metadata
- `GET /.well-known/oauth-protected-resource` — Resource metadata

## Authentication

The server uses Descope for authentication. All MCP endpoints require a valid Bearer token.  
Tokens are validated using FastMCP's built-in `BearerAuthProvider`. Read more about it [here](https://gofastmcp.com/servers/auth/bearer)

## Adding Tools

Just use the `@mcp.tool` decorator:

```python
@mcp.tool
def get_alerts(state: str) -> str:
    ...
```

FastMCP will automatically expose this as an MCP tool!

## Note on Well-Known Endpoints

Ideally, FastMCP should support setting up the `.well-known` endpoints out of the box, similar to how [MCPAuth](https://mcp-auth.dev/docs/configure-server/mcp-auth) works.

For now, this example uses FastAPI to serve these endpoints manually, but future versions of FastMCP may make this even easier.

## Troubleshooting

- If you encounter authentication issues, try clearing the authentication files:
  ```bash
  rm -rf ~/.mcp-auth
  ```
- For OAuth-related issues, check that your `DESCOPE_PROJECT_ID` environment variable is set correctly.
- For outbound app management issues, ensure your `DESCOPE_MANAGEMENT_KEY` is set and has the necessary permissions.
