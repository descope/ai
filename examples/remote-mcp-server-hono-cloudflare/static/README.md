# 🌎 Remote MCP Server with Descope, Hono, and Cloudflare

A template Remote MCP Server with auth by [Descope](https://www.descope.com/), implemented with [Hono](https://hono.dev/), and deployed on [Cloudflare](https://www.cloudflare.com/).

## Quick Start

### Server URL

```
https://brave-search-mcp-server.descope-cx.workers.dev/sse
```

### Configuration

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

## IDE Integration

### Windsurf

1. Open Settings
2. Navigate to **Cascade** → **Model Context Provider Servers**
3. Select **Add Server**

### Cursor

1. Press **Cmd + Shift + J** to open Settings
2. Select **MCP**
3. Select **Add new global MCP server**

### VSCode

1. Read more [here](https://code.visualstudio.com/docs/copilot/chat/mcp-servers)

Note: Requires VSCode 1.99 or above

### Zed

1. Press **CMD + ,** to open settings
2. Add the following configuration:

```json
{
  "context_servers": {
    "brave": {
      "command": {
        "command": "npx",
        "args": [
          "-y",
          "mcp-remote",
          "https://brave-search-mcp-server.descope-cx.workers.dev/sse"
        ]
      }
    },
    "settings": {}
  }
}
```

## Other Clients

### Cloudflare Playground

1. Open [Cloudflare Playground](https://playground.ai.cloudflare.com/)
2. Enter the MCP server URL under MCP Servers
3. Click Connect

## Available Tools

- `web-search`: Search the web with Brave
- `local-search`: Search the local knowledge base with Brave

## Example Workflows

- **Research**: "Find recent articles about quantum computing breakthroughs in the last 6 months"
- **Documentation**: "Search for best practices in documenting Python async functions"
- **Troubleshooting**: "Find solutions for 'ModuleNotFoundError: No module named 'requests'' in Python"
- **Market Analysis**: "Search for recent news about AI startups in the healthcare sector"
- **Learning**: "Find comprehensive tutorials about React hooks and their use cases"
- **Development**: "Search for examples of integrating Brave Search API with Node.js"
- **Security**: "Find recent vulnerabilities reported in popular npm packages"
- **Business Research**: "Search for trends in cloud computing adoption among small businesses"

## Troubleshooting

If you encounter issues with `mcp-remote`, try clearing the authentication files:

```bash
rm -rf ~/.mcp-auth
```
