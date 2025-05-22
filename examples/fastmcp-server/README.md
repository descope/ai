# Python MCP Server using FastMCP and Descope Inbound Apps

![Descope Banner](https://github.com/descope/.github/assets/32936811/d904d37e-e3fa-4331-9f10-2880bb708f64)

## Introduction

This example shows how to secure a Python-based MCP (Model Context Protocol) server using [FastMCP](https://github.com/modelcontext/fastmcp) and Descope Inbound Apps as the main authorization server. It demonstrates how to protect tool calls on an MCP server using Descope-issued OAuth access tokens.

## Preview

You can run this server locally or deploy it to any platform that supports Python (e.g., Railway, Fly.io, or Render).

It’s designed to work with any MCP-compatible client, such as:

- [Cloudflare AI Playground](https://playground.ai.cloudflare.com/)
- [MCP Inspector](https://modelcontextprotocol.io/docs/tools/inspector)
- Custom clients built with the [MCP Client SDK](https://github.com/modelcontext/client)

## Requirements

Before proceeding, ensure you have the following:

- Python 3.8 or later
- A valid Descope [Project ID](https://app.descope.com/settings/project)
- The Descope Inbound Apps feature enabled with proper scopes
- `make` (optional, but simplifies setup)

## Running the Server

First, clone this repo and optionally create a `.env` file (or edit `server.py` directly) with your Descope project details.

### Step 1 – Run using Make:

```bash
make run
```

### Step 2 – Call a Tool

You can test the protected server by calling the `greet` tool with a bearer token:

```python
await client.call_tool("greet", {"name": "Ford"})
```

If the token is valid and includes the required scope (`my_scope`), you’ll get:

```
{'message': 'Hello Ford'}
```

## Authentication

This server uses Descope as its OIDC-compliant OAuth provider.

The server dynamically fetches the JWKS from:

```
https://api.descope.com/v1/apps/<your-project-id>/.well-known/jwks.json
```

## File Structure

```
my-mcp-server/
├── main.py              # Main FastMCP server with Descope auth
├── requirements.txt     # Python dependencies
├── Makefile             # Easy run commands
└── README.md            # Project info
```

## License

MIT
