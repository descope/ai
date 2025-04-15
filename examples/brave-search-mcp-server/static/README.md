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

## With Windsurf

1. Open Windsurf Settings.
2. Under **Cascade**, you'll find **Model Context Provider Servers**.
3. Select **Add Server**.

## With Cursor

1. **Cmd + Shift + J** to open Cursor Settings.
2. Select **MCP**.
3. Select **Add new global MCP server**

## With VSCode

1. Install the MCP extension [here](vscode:mcp/install?name=Sentry&type=sse&url=https%3A%2F%2Fmcp.sentry.dev%2Fsse)

Note: MCP is supported in VSCode 1.99 and above.

## With Cloudflare Playground

1. Open [Cloudflare Playground](https://playground.ai.cloudflare.com/)
2. Under MCP Servers, enter the MCP server URL
3. Click Connect

## With Zed

1. CMD +, to open Zed settings.

```json
{
  "context_servers": {
    "sentry": {
      "command": {
        "command": "npx",
        "args": [
          "-y",
          "mcp-remote",
          "https://mcp.sentry.dev/sse"
        ]
      }
    },
    "settings": {}
  }
}
```

## Workflows

Here's a few sample workflows (prompts) that we've tried to design around within the provider:

- **Research Assistant**: "Find recent articles about quantum computing breakthroughs in the last 6 months"
- **Code Documentation**: "Search for best practices in documenting Python async functions"
- **Technical Troubleshooting**: "Find solutions for 'ModuleNotFoundError: No module named 'requests'' in Python"
- **Competitive Analysis**: "Search for recent news about AI startups in the healthcare sector"
- **Learning Resources**: "Find comprehensive tutorials about React hooks and their use cases"
- **API Integration**: "Search for examples of integrating Brave Search API with Node.js"
- **Security Research**: "Find recent vulnerabilities reported in popular npm packages"
- **Market Research**: "Search for trends in cloud computing adoption among small businesses"

## Available Tools

- `web-search` - Search the web with Brave
- `local-search` - Search the local knowledge base with Brave

## Additional

When using `mcp-remote` to connect to the server, in some rare cases it may help to clear the files added to `~/.mcp-auth`

```bash
rm -rf ~/.mcp-auth
```
