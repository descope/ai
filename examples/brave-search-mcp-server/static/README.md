# Brave Search MCP Server

This service provides a Model Context Protocol (MCP) server for interacting with the [Brave Search API](https://brave.com/search/api/).

This service is maintained by [Descope](https://www.descope.com/) and is very much a proof-of-concept under active development.

```json
{
  "mcpServers": {
    "brave": {
      "command": "npx",
      "args": [
        "-y",
        "mcp-remote",
        "https://brave-search-mcp-server.descope-cx.workers.dev/sse"
      ]
    }
  }
}
```

Or if you just need the server itself (requires an OAuth compatible client):

```json
https://brave-search-mcp-server.descope-cx.workers.dev/sse
```

## With Cursor

## With Windsurf

## With MCP Inspector

## With Cloudflare Playground

## Available Tools

- `web-search` - Search the web with Brave
- `local-search` - Search the local knowledge base with Brave

## Features

The MCP server implementation includes:

- 🔐 OAuth 2.0/2.1 Authorization Server Metadata (RFC 8414)
- 🔑 Dynamic Client Registration (RFC 7591)
- 🎫 Token Revocation (RFC 7009)
- 🔒 PKCE Support
- 📝 Bearer Token Authentication

## Additional

In some rare cases it may help to clear the files added to `~/.mcp-auth`

```bash
rm -rf ~/.mcp-auth
```
