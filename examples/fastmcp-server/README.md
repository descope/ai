# FastMCP Weather Server Example (Python)

![Descope Banner](https://github.com/descope/.github/assets/32936811/d904d37e-e3fa-4331-9f10-2880bb708f64)

## Introduction

This example demonstrates how to implement OAuth authentication with an external provider (Descope) using [FastAPI](https://fastapi.tiangolo.com/) and [FastMCP](https://github.com/fastmcp/fastmcp) for Model Context Protocol (MCP) tools.

Here, FastMCP tools are mounted in a FastAPI server, rather than converting FastAPI APIs to MCP tools.

## Requirements

- Python 3.10+
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
- MCP-compliant tool endpoints
- Modern, self-documenting landing page

## API Endpoints

- `GET /` — Landing page and documentation
- `GET /mcp-server/mcp/` — Main MCP endpoint (requires Bearer token)
- `GET /.well-known/oauth-authorization-server` — OAuth 2.0 server metadata
- `GET /.well-known/oauth-protected-resource` — Resource metadata

## Authentication

The server uses Descope for authentication. All MCP endpoints require a valid Bearer token.  
Tokens are validated using FastMCP’s built-in `BearerAuthProvider`. Read more about it [here](https://gofastmcp.com/servers/auth/bearer)

## Adding Tools

Just use the `@mcp.tool` decorator:

```python
@mcp.tool
def get_alerts(state: str) -> str:
    ...
```

FastMCP will automatically expose this as an MCP tool!

## Note on Well-Known Endpoints

Ideally, FastMCP should support setting up the `.well-known` endpoints out of the box, similar to how [MCPAuth](https://github.com/descope/mcpauth) works.

For now, this example uses FastAPI to serve these endpoints manually, but future versions of FastMCP may make this even easier.

## Troubleshooting

- If you encounter authentication issues, try clearing the authentication files:
  ```bash
  rm -rf ~/.mcp-auth
  ```
- For OAuth-related issues, check that your `DESCOPE_PROJECT_ID` environment variable is set correctly.

**Summary:**

This repo is a reference for building secure, standards-compliant MCP servers with FastAPI and FastMCP, using OAuth for authentication. It demonstrates best practices for mounting tools, handling OAuth metadata, and integrating with real-world identity providers like Descope.
