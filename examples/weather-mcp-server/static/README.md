# 🌤️ Weather MCP Server

A Model Context Protocol (MCP) server for accessing weather data from the [National Weather Service API](https://www.weather.gov/documentation/services-web-api). This service is maintained by [Descope](https://www.descope.com/) and is currently in active development.

## Quick Start

### Server URL

```
https://weather-mcp-server.descope-cx.workers.dev/sse
```

### Configuration

```json
{
  "mcpServers": {
    "weather": {
      "command": "npx",
      "args": [
        "-y",
        "mcp-remote",
        "https://weather-mcp-server.descope-cx.workers.dev/sse"
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
    "weather": {
      "command": {
        "command": "npx",
        "args": [
          "-y",
          "mcp-remote",
          "https://weather-mcp-server.descope-cx.workers.dev/sse"
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

- `get-alerts`: Get weather alerts for a specific state
- `get-forecast`: Get weather forecast for a specific location

## Example Workflows

- **Weather Alerts**: "Get active weather alerts for California"
- **Travel Planning**: "Check the weather forecast for New York City"
- **Event Planning**: "What's the weather forecast for San Francisco this weekend?"
- **Emergency Preparedness**: "Are there any severe weather alerts in Texas?"
- **Agriculture**: "Get the weather forecast for a farm in Iowa"
- **Outdoor Activities**: "Check if there are any weather alerts for hiking in Colorado"
- **Construction**: "Get the weather forecast for a construction site in Chicago"
- **Shipping**: "Check weather conditions for a port in Florida"

## Troubleshooting

If you encounter issues with `mcp-remote`, try clearing the authentication files:

```bash
rm -rf ~/.mcp-auth
```

## Notes

- The weather data is provided by the National Weather Service API
- Only US locations are supported
- No API key is required
- Data is updated frequently and provides accurate weather information
