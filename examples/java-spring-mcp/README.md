# Java Spring MCP Server with Google Calendar Integration

A Model Context Protocol (MCP) server built with Java and Jetty that provides weather information and Google Calendar integration using Descope's outbound app pattern. This server uses Server-Sent Events (SSE) for real-time communication with MCP clients.

## Overview

This MCP server demonstrates:

- **Server-Sent Events (SSE) transport** for real-time MCP communication
- **OAuth 2.1 authentication** with Descope integration
- **Google Calendar integration** using Descope's outbound app pattern
- **Thread-safe authentication** with InheritableThreadLocal for cross-thread auth context

## Features

### Authentication & Authorization

- **OAuth 2.1 Discovery Endpoints**: Automatic OAuth server metadata
- **Bearer Token Validation**: Validates inbound tokens using Descope SDK
- **Scope-Based Access Control**: Each tool requires specific scopes
- **Cross-Thread Authentication**: InheritableThreadLocal for auth context propagation

### Available Tools

- **Calendar Read Tools**: `calendar:read` scope - Get upcoming events and date range events
- **Calendar Search Tool**: `calendar:search` scope - Search events by query
- **Calendar Write Tool**: `calendar:write` scope - Create new calendar events

## Quick Start

### 1. Environment Setup

Create a `.env` file with your Descope configuration:

```bash
# Required
DESCOPE_PROJECT_ID=your_descope_project_id

# Optional
DESCOPE_BASE_URL=https://api.descope.com
MCP_SERVER_PORT=8080
```

### 2. Start the Server

Use the provided start script which automatically loads environment variables:

```bash
./start-server.sh
```

Or run manually with environment variables:

```bash
export DESCOPE_PROJECT_ID=your_descope_project_id
mvn clean compile exec:java -Dexec.mainClass="com.github.stantonk.App"
```

### 3. Connect with MCP Client

The server will be available at:

- **SSE Endpoint**: `http://localhost:8080/sse`
- **OAuth Discovery**: `http://localhost:8080/.well-known/oauth-authorization-server`

## Architecture

### Server Components

#### `App.java` - Main Server

- **Jetty HTTP Server**: Handles HTTP requests and SSE connections
- **OAuth Discovery**: Automatic OAuth 2.1 metadata endpoints
- **MCP Transport**: SSE-based MCP message handling
- **Authentication Servlet**: Validates tokens and sets auth context

#### `AuthenticationService.java` - Token Validation

- **Descope SDK Integration**: Validates inbound tokens
- **User ID Extraction**: Extracts user ID from validated tokens
- **Scope Validation**: Validates required scopes for operations

#### `TokenUtils.java` - Cross-Thread Auth

- **InheritableThreadLocal**: Allows child threads to inherit auth context
- **Scope Validation**: Validates scopes for each tool call
- **Auth Context Management**: Sets and clears authentication info

#### `GoogleCalendarService.java` - Outbound App Integration

- **Manual HTTP Requests**: Direct calls to Descope outbound app API
- **Token Exchange**: Converts inbound tokens to outbound app tokens
- **Google Calendar API**: Makes authenticated requests to Google APIs

### Authentication Flow

```
1. Client Request (with Bearer token)
   ↓
2. Servlet Validation (App.java)
   ↓
3. Token Validation (AuthenticationService.java)
   ↓
4. Set Auth Context (TokenUtils.setAuthInfo())
   ↓
5. MCP Tool Execution (on different thread)
   ↓
6. Get Auth Context (TokenUtils.validateTokenAndGetUser())
   ↓
7. Outbound Token Exchange (GoogleCalendarService.java)
   ↓
8. Google API Call
   ↓
9. Response to Client
```

### Thread Safety

The server uses `InheritableThreadLocal` to solve the cross-thread authentication challenge:

```java
// Servlet thread sets auth info
TokenUtils.setAuthInfo(authToken, userId);

// MCP tool thread (child thread) inherits auth info
TokenUtils.TokenValidationResult auth = TokenUtils.validateTokenAndGetUser(exchange, requiredScopes);
```

## API Reference

### OAuth Endpoints

- `GET /.well-known/oauth-authorization-server` - OAuth server metadata
- `GET /.well-known/openid_configuration` - OpenID Connect configuration

### MCP Endpoints

- `GET /sse` - Server-Sent Events endpoint for MCP communication
- `POST /mcp/message` - MCP message handling

### Tool Definitions

#### Calendar Tools

```json
{
  "get_upcoming_events": {
    "description": "Get upcoming calendar events",
    "parameters": {
      "max_results": { "type": "number", "default": 10 }
    }
  },
  "get_events_by_date_range": {
    "description": "Get events within date range",
    "parameters": {
      "start_date": { "type": "string", "pattern": "^\\d{4}-\\d{2}-\\d{2}$" },
      "end_date": { "type": "string", "pattern": "^\\d{4}-\\d{2}-\\d{2}$" }
    }
  },
  "search_events": {
    "description": "Search events by query",
    "parameters": {
      "query": { "type": "string", "minLength": 1 }
    }
  },
  "create_calendar_event": {
    "description": "Create new calendar event",
    "parameters": {
      "event_data": {
        "type": "string",
        "description": "JSON string containing event details"
      }
    }
  }
}
```

## Configuration

### Environment Variables

| Variable             | Required | Default                   | Description             |
| -------------------- | -------- | ------------------------- | ----------------------- |
| `DESCOPE_PROJECT_ID` | Yes      | -                         | Your Descope project ID |
| `DESCOPE_BASE_URL`   | No       | `https://api.descope.com` | Descope API base URL    |
| `MCP_SERVER_PORT`    | No       | `8080`                    | Server port             |
| `MCP_SERVER_HOST`    | No       | `localhost`               | Server host             |

### Descope Setup

1. **Create Outbound App**: Configure Google Calendar outbound app in Descope console
2. **App ID**: The outbound app ID is hardcoded as `"google-calendar"`
3. **OAuth Scopes**: Configure appropriate Google Calendar scopes
4. **User Permissions**: Ensure users have required scopes for tool access

## Development

### Project Structure

```
src/main/java/com/github/stantonk/
├── App.java                    # Main server with Jetty and MCP setup
├── AuthenticationService.java  # Token validation and user extraction
├── TokenUtils.java            # Cross-thread authentication utilities
├── GoogleCalendarService.java # Outbound app and Google Calendar integration
└── WeatherService.java        # National Weather Service integration
```

### Key Implementation Details

#### Manual Outbound App Token Exchange

Instead of using Descope SDK's outbound app methods, we make direct HTTP requests:

```java
// Authorization header format: Bearer project_id:inbound_token
String authHeader = String.format("Bearer %s:%s", projectId, cleanToken);

// Request body
String requestBody = String.format(
    "{\"appId\": \"%s\", \"userId\": \"%s\"}",
    GOOGLE_OUTBOUND_APP_ID,
    userId
);
```

#### Thread-Safe Authentication

Using `InheritableThreadLocal` to pass auth context from servlet to tool threads:

```java
private static final InheritableThreadLocal<String> currentAuthToken = new InheritableThreadLocal<>();
private static final InheritableThreadLocal<String> currentUserId = new InheritableThreadLocal<>();
```

## Troubleshooting

### Common Issues

1. **"DESCOPE_PROJECT_ID environment variable is not set"**

   - Ensure `.env` file exists with correct project ID
   - Or export environment variable: `export DESCOPE_PROJECT_ID=your_id`

2. **"No authentication info found"**

   - Check that Bearer token is provided in Authorization header
   - Verify token is valid and not expired

3. **"Request project is invalid or missing"**

   - Verify `DESCOPE_PROJECT_ID` is correct
   - Check that project ID is properly set in environment

4. **Cross-thread authentication errors**
   - Server uses `InheritableThreadLocal` for thread safety
   - Auth context is automatically inherited by child threads

### Logging

The server uses SLF4J with Logback for logging. Set log levels in `logback.xml`:

```xml
<logger name="com.github.stantonk" level="DEBUG"/>
<logger name="com.descope" level="DEBUG"/>
```

## License

This project is licensed under the MIT License.
